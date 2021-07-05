from typing import Iterable, List, Reversible, Tuple
import textwrap

import tcod
import pygame

import colors

def text_to_screen(screen, text = '', color = colors.white, size = 16, position = (0, 0), font = 'arial'):
    font = pygame.font.SysFont(font, size)
    image = font.render(text, True, color)
    screen.blit(image, position)

class Message:
    def __init__(self, text: str, fg: Tuple[int, int, int]):
        self.plain_text = text
        self.fg = fg
        self.count = 1

    @property
    def full_text(self) -> str:
        """The full text of this message, including the count if necessary."""
        if self.count > 1:
            return f"{self.plain_text} (x{self.count})"
        return self.plain_text

class MessageLog:
    def __init__(self) -> None:
        self.messages: List[Message] = []

    def add_message(
        self, text: str, fg: Tuple[int, int, int] = colors.white, *, stack: bool= True,
    ) -> None:
        """Add a message to this log.
        `text` is the message text, `fg` is the text color.
        If `stack` is True then the message can stack with a previous message
        of the same text.
        """
        if stack and self.messages and text == self.messages[-1].plain_text:
            self.messages[-1].count += 1
        else:
            self.messages.append(Message(text, fg))

    def render(self, screen: pygame.display) -> None:
        """Render this log over the given area.
        `x`, `y`, `width`, `height` is the rectangular region to render onto
        the `console`.
        """
        self.render_messages(screen, x, y, width, height, self.messages)

    @staticmethod
    def wrap(string: str, width: int) -> Iterable[str]:
        """Return a wrapped text message."""
        for line in string.splitlines(): # Handle newlines in messages.
            yield from textwrap.wrap(
                line, width, expand_tabs = True,
            )

    @classmethod
    def render_messages(
        cls,
        screen: pygame.display,
        x: int,
        y: int,
        width: int,
        height: int,
        messages: Reversible[Message],
    ) -> None:
        """Render the messages provided.
        The `messages` are rendered starting at  the last message and working
        backwards.
        """
        block_size = 16
        y_offset = height - 1
        mess_box = pygame.Surface((width*block_size, height*block_size))
        mess_box.fill((0, 0, 0))
        for message in reversed(messages):
            for line in reversed(list(cls.wrap(message.full_text, width))):
                text_to_screen(mess_box, text = line, position = (0*block_size, y_offset*block_size))
                y_offset -= 1
                if y_offset < 0:
                    screen.blit(mess_box, (x*block_size, y*block_size))
                    return # No more space to print messages.
        
