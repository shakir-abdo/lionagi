# Copyright (c) 2023 - 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Defines `AssistantResponse`, a specialized `RoledMessage` for the AI's
assistant replies (usually from LLM or related).
"""
from typing import Any

from pydantic import BaseModel

from lionagi.utils import copy, is_same_dtype

from .base import MessageRole, SenderRecipient
from .message import MessageRole, RoledMessage, Template, jinja_env


def prepare_assistant_response(
    assistant_response: BaseModel | list[BaseModel] | dict | str | Any, /
) -> dict:
    if assistant_response:
        content = {}
        # Handle model.choices[0].message.content format
        if isinstance(assistant_response, BaseModel):
            content["assistant_response"] = (
                assistant_response.choices[0].message.content or ""
            )
            content["model_response"] = assistant_response.model_dump(
                exclude_none=True, exclude_unset=True
            )
        # Handle streaming response[i].choices[0].delta.content format
        elif isinstance(assistant_response, list):
            if is_same_dtype(assistant_response, BaseModel):
                msg = "".join(
                    [
                        i.choices[0].delta.content or ""
                        for i in assistant_response
                    ]
                )
                content["assistant_response"] = msg
                content["model_response"] = [
                    i.model_dump(
                        exclude_none=True,
                        exclude_unset=True,
                    )
                    for i in assistant_response
                ]
            elif is_same_dtype(assistant_response, dict):
                msg = "".join(
                    [
                        i["choices"][0]["delta"]["content"] or ""
                        for i in assistant_response
                    ]
                )
                content["assistant_response"] = msg
                content["model_response"] = assistant_response
        elif isinstance(assistant_response, dict):
            if "content" in assistant_response:
                content["assistant_response"] = assistant_response["content"]
            elif "choices" in assistant_response:
                content["assistant_response"] = assistant_response["choices"][
                    0
                ]["message"]["content"]
            content["model_response"] = assistant_response
        elif isinstance(assistant_response, str):
            content["assistant_response"] = assistant_response
        else:
            content["assistant_response"] = str(assistant_response)
        return content
    else:
        return {"assistant_response": ""}


class AssistantResponse(RoledMessage):
    """
    A message representing the AI assistant's reply, typically
    from a model or LLM call. If the raw model output is available,
    it's placed in `metadata["model_response"]`.
    """

    template: Template | str | None = jinja_env.get_template(
        "assistant_response.jinja2"
    )

    @property
    def response(self) -> str:
        """Get or set the text portion of the assistant's response."""
        return copy(self.content["assistant_response"])

    @response.setter
    def response(self, value: str) -> None:
        self.content["assistant_response"] = value

    @property
    def model_response(self) -> dict | list[dict]:
        """
        Access the underlying model's raw data, if available.

        Returns:
            dict or list[dict]: The stored model output data.
        """
        return copy(self.metadata.get("model_response", {}))

    @classmethod
    def create(
        cls,
        assistant_response: BaseModel | list[BaseModel] | dict | str | Any,
        sender: SenderRecipient | None = None,
        recipient: SenderRecipient | None = None,
        template: Template | str | None = None,
        **kwargs,
    ) -> "AssistantResponse":
        """
        Build an AssistantResponse from arbitrary assistant data.

        Args:
            assistant_response:
                A pydantic model, list, dict, or string representing
                an LLM or system response.
            sender (SenderRecipient | None):
                The ID or role denoting who sends this response.
            recipient (SenderRecipient | None):
                The ID or role to receive it.
            template (Template | str | None):
                Optional custom template.
            **kwargs:
                Additional content key-value pairs.

        Returns:
            AssistantResponse: The constructed instance.
        """
        content = prepare_assistant_response(assistant_response)
        model_response = content.pop("model_response", {})
        content.update(kwargs)
        params = {
            "content": content,
            "role": MessageRole.ASSISTANT,
            "recipient": recipient or MessageRole.USER,
        }
        if sender:
            params["sender"] = sender
        if template:
            params["template"] = template
        if model_response:
            params["metadata"] = {"model_response": model_response}
        return cls(**params)

    def update(
        self,
        assistant_response: (
            BaseModel | list[BaseModel] | dict | str | Any
        ) = None,
        sender: SenderRecipient | None = None,
        recipient: SenderRecipient | None = None,
        template: Template | str | None = None,
        **kwargs,
    ):
        """
        Update this AssistantResponse with new data or fields.

        Args:
            assistant_response:
                Additional or replaced assistant model output.
            sender (SenderRecipient | None):
                Updated sender.
            recipient (SenderRecipient | None):
                Updated recipient.
            template (Template | str | None):
                Optional new template.
            **kwargs:
                Additional content updates for `self.content`.
        """
        if assistant_response:
            content = prepare_assistant_response(assistant_response)
            self.content.update(content)
        super().update(
            sender=sender, recipient=recipient, template=template, **kwargs
        )


# File: lionagi/protocols/messages/assistant_response.py
