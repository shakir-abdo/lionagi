"""
the base directive
"""

import asyncio
import re
import contextlib
from abc import ABC
from typing import Any

from lionagi.libs.ln_convert import to_dict, to_list
from lionagi.libs.ln_nested import get_flattened_keys, nget
from lionagi.libs.ln_func_call import lcall, alcall
from lionagi.libs.ln_parse import ParseUtil, StringMatch

from ..generic import Model
from ..message import Instruction, AssistantResponse, ActionRequest, ActionResponse
from ..message.util import _parse_action_request


oai_fields = [
    "id", "object", "created", "model", "choices", "usage", "system_fingerprint"
]

choices_fields = [
    "index", "message", "logprobs", "finish_reason"
]

usage_fields = [
    "prompt_tokens", "completion_tokens", "total_tokens"
]




class BaseDirective(ABC):

    default_template = None

    def __init__(self, branch, model: Model = None, template_=None) -> None:
        self.branch = branch
        if model and isinstance(model, Model):
            branch.model = model
            self.model = model
        else:
            self.model = branch.model
        self.form_template = template_ or self.default_template

    @property
    def class_name(self) -> str:
        return self._class_name()

    @classmethod
    def _class_name(cls) -> str:
        return cls.__name__

    def _create_chat_config(
        self,
        system=None,
        instruction=None,
        context=None,
        sender=None,
        recipient=None,
        requested_fields=None,
        form=None,
        tools=False,
        **kwargs,
    ) -> Any:

        if system:
            self.branch.add_message(system=system)

        if not form:
            self.branch.add_message(
                instruction=instruction,
                context=context,
                sender=sender,
                recipient=recipient,
                requested_fields=requested_fields,
            )

        else:
            instruct_ = Instruction.from_form(form)
            self.branch.add_message(instruction=instruct_)

        if "tool_parsed" in kwargs:
            kwargs.pop("tool_parsed")
            tool_kwarg = {"tools": tools}
            kwargs = tool_kwarg | kwargs

        elif tools and self.branch.has_tools:
            kwargs = self.branch.tool_manager.parse_tool(tools=tools, **kwargs)

        config = {**self.model.config, **kwargs}
        if sender is not None:
            config["sender"] = sender

        return config

    async def _call_chatcompletion(self, **kwargs):
        return await self.model.call_chat_completion(
            self.branch.to_chat_messages(), **kwargs
        )

    async def _process_chatcompletion(self, payload, completion, sender, invoke_tool=False):
        
        # process the raw chat completion response
        _msg = None
        if "choices" in completion:
            
            aa = payload.pop("messages", None)
            self.branch.update_last_instruction_meta(payload)
            msg = completion.pop("choices", None)
            if msg and isinstance(msg, list):
                msg = msg[0]
            
            if isinstance(msg, dict):
                _msg = msg.pop("message", None)
                completion.update(msg)
                                    
                self.branch.add_message(
                    assistant_response=_msg, metadata=completion, sender=sender
                )
                self.branch.model.status_tracker.num_tasks_succeeded += 1
        else:
            self.branch.model.status_tracker.num_tasks_failed += 1

        # if the assistant response contains action request, we add each as a message to branch
        a = _parse_action_request(_msg)
        if a is None:
            return _msg
        
        if a:
            for i in a:
                if i.function in self.branch.tool_manager.registry:
                    i.recipient = self.branch.tool_manager.registry[i.function].ln_id   # recipient is the tool
                else:
                    raise ValueError(f"Tool {i.function} not found in registry")
                self.branch.add_message(action_request=i, recipient=i.recipient)

        if invoke_tool:
            # invoke tools and add action response to branch
            tasks = []
            for i in a:
                tool = self.branch.tool_manager.registry[i.function]
                tasks.append(asyncio.create_task(tool.invoke(i.arguments)))
            
            results = await asyncio.gather(*tasks)
            results = to_list(results, flatten=True)
            
            for _result, _request in zip(results, a):
                self.branch.add_message(
                    action_request=_request, 
                    func_outputs=_result,
                    sender=_request.recipient,
                )
                
        return None

    async def _output(
        self,
        payload, 
        completion, 
        sender,
        invoke_tool,
        out,
        requested_fields,
        form=None,
        return_form=True,
    ):
        content_ = await self._process_chatcompletion(
            payload=payload, 
            completion=completion, 
            sender=sender, 
            invoke_tool=invoke_tool
        )
        
        if content_ is None:
            return None
    
        response_ = self._process_model_response(content_, requested_fields)

        if form:
            form._process_response(response_)
            return form if return_form else form.outputs

        if out:
            return response_


    @staticmethod
    def _process_model_response(content_, requested_fields):
        out_ = ""

        if len(content_.items()) == 1 and len(get_flattened_keys(content_)) == 1:
            key = get_flattened_keys(content_)[0]
            out_ = content_[key]

        if requested_fields:
            with contextlib.suppress(Exception):
                return StringMatch.force_validate_dict(out_, requested_fields)

        if isinstance(out_, str):
            with contextlib.suppress(Exception):
                match = re.search(r"```json\n({.*?})\n```", out_, re.DOTALL)
                if match:
                    out_ = ParseUtil.fuzzy_parse_json(match.group(1))

        return out_