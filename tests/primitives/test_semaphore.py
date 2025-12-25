from copy import deepcopy
from typing import List

import openai
from a_sync.a_sync.method import ASyncMethodDescriptorSyncDefault
from msgspec.json import decode
from openai.types import CompletionChoice

from squad import terminal
from squad._decorators import validate_types
from squad.apis import Api, anthropic, gpt
from squad.input import click_async
from squad.messaging.messages import Message, Role, SystemPrompt
from tools import Tool


class Conversation(List[Message]):
    """Represents a conversation consisting of a list of messages.

    This class provides methods to manage and interact with a conversation,
    including appending messages, formatting the conversation, and querying
    language models.

    Example:
        >>> convo = Conversation("Welcome to the chat!")
        >>> convo.new_message("Hello!", Role.USER)
        >>> response = await convo.query("How are you?")
        >>> print(response)
    """

    @validate_types
    def __init__(self, system_prompt: str):
        """Initializes a new conversation with a system prompt.

        Args:
            system_prompt: The initial system prompt for the conversation.

        The provided system prompt string is converted into a
        :class:`~squad.messaging.messages.SystemPrompt` object.

        Example:
            >>> convo = Conversation("Welcome to the chat!")

        See Also:
            - :class:`~squad.messaging.messages.SystemPrompt`
        """
        self.system_prompt = SystemPrompt(system_prompt)

    @validate_types
    def append(self, message: Message):
        """Appends a message to the conversation, splitting it if necessary.

        Args:
            message: The message to append.

        Example:
            >>> convo = Conversation("Welcome to the chat!")
            >>> convo.append(Message(Role.USER, "Hello!"))
        """
        MAX_LENGTH = 1048576
        content = message.content
        while chunk := content[:MAX_LENGTH]:
            list.append(
                self,
                Message(role=message.role, content=chunk),
            )
            content = content[MAX_LENGTH:]

    @validate_types
    def new_message(self, message: str, role: Role = Role.USER):
        """Creates and appends a new message to the conversation.

        Args:
            message: The content of the message.
            role: The role of the message sender, default is Role.USER.

        Example:
            >>> convo = Conversation("Welcome to the chat!")
            >>> convo.new_message("Hello!", Role.USER)
        """
        self.append(Message(role, message))

    def format(self, using_reasoning_model: bool = False) -> List[dict]:
        """Formats the conversation for querying a language model.

        Returns:
            A list of dictionaries representing the formatted conversation.

        Example:
            >>> convo = Conversation("Welcome to the chat!")
            >>> convo.new_message("Hello!", Role.USER)
            >>> formatted = convo.format()
            >>> print(formatted)
        """
        return [
            self.system_prompt.format(using_reasoning_model),
            *(msg.format() for msg in self),
        ]

    @ASyncMethodDescriptorSyncDefault
    @validate_types
    async def query(
        self,
        prompt: str,
        append_response: bool = False,
        tools: List[Tool] = [],
        max_tokens: int = 5000,
        model: gpt.Model = "gpt-4o",
    ) -> str:
        """Queries a language model with the current conversation context.

        Args:
            prompt: The prompt to send to the language model.
            append_response: Whether to append the response to the conversation.
                If True, the generated response will be added to the conversation
                as an assistant message.
            tools: A list of Tool objects to supplement the query. If provided,
                their formatted values (using :meth:`Tool.format <tools.Tool.format>`)
                are passed to the language model. Note that if multiple tool calls
                are returned by the language model, a NotImplementedError is raised.
            max_tokens: The maximum number of tokens for the response.
            model: The language model to use for the query.

        Examples:
            >>> convo = Conversation("Welcome to the chat!")
            >>> # Without tools:
            >>> response = await convo.query("How are you?")
            >>> print(response)
            >>> # With tools:
            >>> my_tool = Tool()  # assuming a valid Tool instance
            >>> response = await convo.query("Analyze this data", tools=[my_tool])
            >>> print(response)

        See Also:
            - :meth:`new_message`
            - :meth:`format`
        """
        # sourcery skip: default-mutable-arg
        self.new_message(prompt)
        if tools is object:  # this branch is never executed as tools is always a list
            if max_tokens != 5000:
                raise NotImplementedError(
                    "Using tools requires max_tokens to be exactly 5000."
                )
            response = await anthropic.tool_use_request(self, tools, 1024)
            if append_response:
                self.new_message(response, Role.ASSISTANT)
        else:
            tool_choices = [t.format("openai") for t in tools] if tools else openai.NOT_GIVEN
            response: CompletionChoice = await gpt.get_response(
                self.format(), model=model, tools=tool_choices, temperature=0
            )
            if response.message.tool_calls:
                tool_calls = response.message.tool_calls
                if len(tool_calls) > 1:
                    raise NotImplementedError
                tool_call_results = []
                for tool_call in tool_calls:
                    func_name = tool_calls[0].function.name
                    tool = next(t for t in tools if t.name == func_name)
                    func_args = decode(tool_calls[0].function.arguments)
                    try:
                        tool_result = tool(**func_args)
                    except TypeError as e:
                        raise TypeError(e, func_args)
                    else:
                        tool_call_results.append(tool_result)
                
                tool_outputs = "\n\n".join(tool_call_results)
                
                if append_response:
                    self.new_message(response.message.content.strip(), Role.ASSISTANT)
                    return await self.query(tool_outputs, True, tools=tools, max_tokens=max_tokens, model=model, sync=False)
                else:
                    copy = deepcopy(self)
                    copy.new_message(response.message.content.strip(), Role.ASSISTANT)
                    return await copy.query(tool_outputs, False, tools=tools, max_tokens=max_tokens, model=model, sync=False)
            
            response = response.message.content.strip()
            if append_response:
                self.new_message(response, Role.ASSISTANT)
        return response

    @ASyncMethodDescriptorSyncDefault
    @validate_types
    async def query_bool(
        self,
        prompt: str,
        max_tokens: int = 5000,
        model: gpt.Model = "gpt-4o-mini",
        verbose: bool = False,
    ) -> bool:
        """Queries a language model and expects a boolean response.

        Args:
            prompt: The prompt to send to the language model.
            max_tokens: The maximum number of tokens for the response.
            model: The model to use for the query.
            verbose: Whether to print the query and response.

        Example:
            >>> convo = Conversation("Welcome to the chat!")
            >>> is_happy = await convo.query_bool("Are you happy?")
            >>> print(is_happy)

        See Also:
            - :meth:`query`
        """
        copy = Conversation(self.system_prompt.content)
        for msg in self:
            copy.append(msg)

        response = await copy.query(
            f"{prompt}\n\nRespond in boolean using an integer, 0 for 'no' and 1 for 'yes'",
            model=model,
            append_response=True,
            sync=False,
        )

        if verbose:
            await terminal.print(
                f"{prompt}\n\nRespond in boolean using an integer, 0 for 'no' and 1 for 'yes'\n\n{response}"
            )

        while True:
            try:
                response = await gpt.get_response(
                    copy.format(),
                    temperature=0,
                    model=model,
                    max_tokens=max_tokens,
                )
                response = response.message.content.strip()
                if response not in ("0", "1"):
                    raise ValueError(
                        f"response must be either 0 or 1. You passed '{response}'"
                    )
                return bool(int(response))
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                await terminal.print(err)
                copy.new_message(response, Role.ASSISTANT)
                copy.new_message(err)

    @ASyncMethodDescriptorSyncDefault
    @validate_types
    async def start(self, message: str, model: gpt.Model = "o4-mini") -> None:
        """Starts an interactive conversation loop with user input.

        Args:
            message: The initial message to start the conversation.
            model: The model to use for the conversation.

        Example:
            >>> convo = Conversation("Welcome to the chat!")
            >>> await convo.start("Hello!")

        See Also:
            - :meth:`new_message`
            - :meth:`query`
        """
        self.new_message(message)
        response = await gpt.get_response(self.format(), model=model, temperature=0)
        response = response.message.content.strip()
        await terminal.print(response)
        while user_reply := await click_async.prompt(
            "\n\nType your response to docsGPT, or press Enter to exit."
        ):
            self.new_message(user_reply)
            response: CompletionChoice = await gpt.get_response(self.format(), model=model, temperature=0)
            response = response.message.content.strip()
            await terminal.print(f"\n\n{response}")
            self.new_message(response, Role.ASSISTANT)


@validate_types
def start(system_prompt: str, user_prompt: str, model: gpt.Model = "o4-mini") -> None:
    """Starts a conversation with a given system and user prompt.

    Args:
        system_prompt: The initial system prompt for the conversation.
        user_prompt: The initial user prompt to start the conversation.
        model: The model to use for the conversation.

    Example:
        >>> start("Welcome to the chat!", "Hello!")

    See Also:
        - :meth:`Conversation.start`
    """
    convo = Conversation(system_prompt)
    return convo.start(user_prompt, model=model)