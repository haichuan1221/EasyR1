# Copyright 2024 Bytedance Ltd. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import math
import os
from collections import defaultdict
from io import BytesIO
from typing import Any, Dict, List, Optional, Union

import numpy as np
import torch
from datasets import load_dataset,load_from_disk
from PIL import Image
from PIL.Image import Image as ImageObject
from torch.utils.data import Dataset
from transformers import PreTrainedTokenizer, ProcessorMixin

from ..models.transformers.qwen2_vl import get_rope_index
from . import torch_functional as VF


def collate_fn(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    tensors = defaultdict(list)
    non_tensors = defaultdict(list)
    for feature in features:
        for key, value in feature.items():
            if isinstance(value, torch.Tensor):
                tensors[key].append(value)
            else:
                non_tensors[key].append(value)

    for key, value in tensors.items():
        tensors[key] = torch.stack(value, dim=0)

    for key, value in non_tensors.items():
        non_tensors[key] = np.array(value, dtype=object)

    return {**tensors, **non_tensors}


def process_image(image: Union[Dict[str, Any], ImageObject], max_pixels: int, min_pixels: int) -> ImageObject:
    if isinstance(image, dict):
        image = Image.open(BytesIO(image["bytes"]))

    if (image.width * image.height) > max_pixels:
        resize_factor = math.sqrt(max_pixels / (image.width * image.height))
        width, height = int(image.width * resize_factor), int(image.height * resize_factor)
        image = image.resize((width, height))

    if (image.width * image.height) < min_pixels:
        resize_factor = math.sqrt(min_pixels / (image.width * image.height))
        width, height = int(image.width * resize_factor), int(image.height * resize_factor)
        image = image.resize((width, height))

    if image.mode != "RGB":
        image = image.convert("RGB")

    return image


class RLHFDataset(Dataset):
    """
    We assume the dataset contains a column that contains prompts and other information
    """

    def __init__(
        self,
        data_path: str,
        tokenizer: PreTrainedTokenizer,
        processor: Optional[ProcessorMixin],
        prompt_key: str = "prompt",
        answer_key: str = "answer",
        image_key: str = "images",
        max_prompt_length: int = 1024,
        truncation: str = "error",
        system_prompt: str = None,
        max_pixels: int = None,
        min_pixels: int = None,
    ):
        self.tokenizer = tokenizer
        self.processor = processor
        self.prompt_key = prompt_key
        self.answer_key = answer_key
        self.image_key = image_key
        self.max_prompt_length = max_prompt_length
        self.truncation = truncation
        self.system_prompt = system_prompt
        self.max_pixels = max_pixels
        self.min_pixels = min_pixels

        if "@" in data_path:
            data_path, data_split = data_path.split("@")
        else:
            data_split = "train"

        if os.path.isdir(data_path):
            self.dataset = load_dataset("parquet", data_dir=data_path, split="train")
        elif os.path.isfile(data_path):
            self.dataset = load_dataset("parquet", data_files=data_path, split="train")
        else:  # remote dataset
            self.dataset = load_dataset(data_path, split=data_split)

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, index):
        row_dict: dict = self.dataset[index]
        messages = [{"role": "user", "content": row_dict[self.prompt_key]}]
        if self.system_prompt:
            messages.insert(0, {"role": "system", "content": self.system_prompt})
        else:
            messages.insert(0,{"role": "system", "content": """# 身份描述
- 你是一个数据搜索大师，你精通各种查询数据的逻辑，擅长将用户的搜索需求拆解为合适的搜索条件，以此帮用户找到他需要的数据。

# 你的职责

## 职责概述
- 你一共可以做两件事情：「输出 DSL 搜索语句」和「反馈问题」，这两件事情二选一进行执行。
- 输出 DSL 搜索语句：根据用户输入的 Search Requirement ，按最优的方式输出 OpenSearch DSL 查询语句。
- 反馈问题：当搜索需求在可选数据表内无法搜索到，需要反馈搜索需求无法满足，并反馈无法满足的原因。

## 搜索原则
- 你输出搜索语句的查询结果会根据相关性进行重新排序，然后展现给用户。
- 要尽可能覆盖用户的搜索需求，可以适当的扩大时间搜索范围，以确保搜索的结果中能包含用户想要搜索的目标数据
  - 比如「刚刚」，可以查询1小时、几天内的内容。
- 需要区分 Search Requirement 中自然语言的某个词，到底是搜索关键字还是目标数据表。
- 搜索语句需要基于 Data Table 编写，不能创造 Data Table 以外的数据表和字段。
- Pay attention to the year of the date and time.
- 输出的语言必须跟用户输入的语言保持一致。

## DSL 语句的使用规范
### 每种字段类型的查询规则
- keyword ：使用 term 查询。
- text ：使用 match 或 match_phrase 查询。
- date ：使用 range 查询。必须输出包含时区偏移的 ISO 8601 格式日期时间。
- long ：使用 term 或 range 查询。
### 其他使用规则
- RRULE 字段的搜索方式：直接在 RRULE 的字段内输出 RRULE 语句。

# 你能得到的信息
- Search Requirement：一段自然语言描述，表明了用户想要搜索什么数据。
- Current time：用户当前时间。
- Data Table：可供查询的数据表，描述了表以及表字段。

# 你要输出的信息
### 结构展示
<think>
//思考过程
</think>
<answer>
{
  "bizDslQueryMap":  // 搜索语句。输出应为有效的 OpenSearch DSL 查询，格式为 JSON，且符合 OpenSearch 的 DSL 语法规范。
  {
    "index_1": // 目标数据表及搜索语句
    {
     xxxx
    }
  },
  "unableSearch": bool, 如果可选数据表中没办法满足用户搜索需求，请输出 true 。
  "unableSearchMessage": ""  // 在这个字段内容输出哪部分搜索需求无法覆盖。
}
</answer>"""})

        prompt = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)

        if self.image_key in row_dict:
            prompt = prompt.replace("<image>", "<|vision_start|><|image_pad|><|vision_end|>")
            row_dict["multi_modal_data"] = {
                "image": [
                    process_image(image, self.max_pixels, self.min_pixels) for image in row_dict.pop(self.image_key)
                ]
            }
            model_inputs = self.processor(row_dict["multi_modal_data"]["image"], prompt, return_tensors="pt")
            input_ids = model_inputs.pop("input_ids")[0]
            attention_mask = model_inputs.pop("attention_mask")[0]
            row_dict["multi_modal_inputs"] = dict(model_inputs)
            position_ids = get_rope_index(
                self.processor,
                input_ids=input_ids,
                image_grid_thw=model_inputs["image_grid_thw"],
                attention_mask=attention_mask,
            )  # (3, seq_length)
        else:
            model_inputs = self.tokenizer([prompt], add_special_tokens=False, return_tensors="pt")
            input_ids = model_inputs.pop("input_ids")[0]
            attention_mask = model_inputs.pop("attention_mask")[0]
            position_ids = torch.clip(attention_mask.cumsum(dim=0) - 1, min=0, max=None)  # (seq_length,)

        input_ids, attention_mask, position_ids = VF.postprocess_data(
            input_ids=input_ids,
            attention_mask=attention_mask,
            position_ids=position_ids,
            max_length=self.max_prompt_length,
            pad_token_id=self.tokenizer.pad_token_id,
            left_pad=True,
            truncation=self.truncation,
        )
        row_dict["input_ids"] = input_ids
        row_dict["attention_mask"] = attention_mask
        row_dict["position_ids"] = position_ids
        row_dict["raw_prompt_ids"] = self.tokenizer.encode(prompt, add_special_tokens=False)
        row_dict["ground_truth"] = row_dict.pop(self.answer_key)
        return row_dict
