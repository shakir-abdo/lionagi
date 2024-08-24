import inspect

from abc import ABC
import asyncio
from typing import Any

import numpy as np

from lion_core.generic.component import Component
from lion_core.exceptions import LionResourceError, LionTypeError


from lionagi.os.primitives import Log
from lionagi.os.service.schema import ModelConfig, EndpointSchema

from lionagi.os.libs import nget, to_str, to_list
from lionagi.os.primitives import note, pile, Note


from .imodel import iModel


class iModelExtension(ABC):

    @staticmethod
    async def compute_perplexity(
        imodel: iModel,
        initial_context: str = None,
        tokens: list[str] = None,
        system_msg: str = None,
        n_samples: int = 1,  # number of samples used for the computation
        use_residual: bool = True,  # whether to use residue for the last sample
        **kwargs,  # additional arguments for the model
    ) -> tuple[list[str], float]:
        tasks = []
        context = initial_context or ""

        n_samples = n_samples or len(tokens)
        sample_token_len, residual = divmod(len(tokens), n_samples)
        samples = []

        if n_samples == 1:
            samples = [tokens]
        else:
            samples = [tokens[: (i + 1) * sample_token_len] for i in range(n_samples)]

            if use_residual and residual != 0:
                samples.append(tokens[-residual:])

        sampless = [context + " ".join(sample) for sample in samples]

        for sample in sampless:
            messages = [{"role": "system", "content": system_msg}] if system_msg else []
            messages.append(
                {"role": "user", "content": sample},
            )

            task = asyncio.create_task(
                await imodel.call(
                    input_=messages,
                    endpoint="chat/completions",
                    logprobs=True,
                    max_tokens=sample_token_len,
                    **kwargs,
                )
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)  # result is (payload, response)
        results_ = []
        num_prompt_tokens = 0
        num_completion_tokens = 0

        for idx, result in enumerate(results):
            _dict = {}
            _dict["tokens"] = samples[idx]
            result = note(**result)
            num_prompt_tokens += result.get([1, "usage", "prompt_tokens"], 0)
            num_completion_tokens += result.get([1, "usage", "completion_tokens"], 0)
            logprobs = result.get([1, "choices", 0, "logprobs", "content"], [])
            logprobs = to_list(logprobs, flatten=True, dropna=True)
            _dict["logprobs"] = [(i["token"], i["logprob"]) for i in logprobs]
            results_.append(_dict)

        logprobs = to_list(
            [[i[1] for i in d["logprobs"]] for d in results_], flatten=True
        )

        return {
            "tokens": tokens,
            "n_samples": n_samples,
            "num_prompt_tokens": num_prompt_tokens,
            "num_completion_tokens": num_completion_tokens,
            "logprobs": logprobs,
            "perplexity": np.exp(np.mean(logprobs)),
        }

    @staticmethod
    async def embed_node(
        node: Any, imodel: iModel, field="content", **kwargs
    ) -> Component:
        """
        if not specify field, we embed node.content
        """
        if not isinstance(node, Component):
            raise LionTypeError("node must be a Component or its subclass object")

        embed_str = getattr(node, field)

        if isinstance(embed_str, Note):
            embed_str = embed_str.to_dict()
        if isinstance(embed_str, dict) and "images" in embed_str:
            embed_str.pop("images", None)
            embed_str.pop("image_detail", None)

        if not "embeddings" in imodel.service.active_endpoints:
            imodel.service.add_endpoint("embeddings")

        embed_str = to_str(embed_str)

        endpoint = imodel.service.active_endpoints["embeddings"]
        endpoint_schema = endpoint.schema
        model = endpoint_schema.default_model_config["model"]
        token_limit = endpoint_schema.token_limit
        num_tokens = endpoint.token_calculator.calculate(to_str(embed_str))

        if token_limit and num_tokens > token_limit:
            raise LionResourceError(
                f"Number of tokens {num_tokens} exceeds the limit of {token_limit} tokens for model {model}"
            )

        api_calling: Log = await imodel.embed(embed_str=embed_str, **kwargs)

        payload: dict = api_calling.content["payload"]
        loginfo: dict = api_calling.loginfo.to_dict()

        payload.pop("input", None)
        loginfo.update(payload)

        node.embedding = api_calling.content.get(
            ["response", "data", 0, "embedding"],
            [],
        )

        node.metadata.update("embedding_meta", loginfo)
        return node
