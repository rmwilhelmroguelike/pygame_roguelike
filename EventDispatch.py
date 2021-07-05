import tcod
import tcod.event
import pygame
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    Mapping,
    NamedTuple,
    Optional,
    Tuple,
    TypeVar,
)

T = TypeVar("T")

Point = NamedTuple("Point", [("x", int), ("y", int)])

def get() -> Iterator[Any]:
    """Return an iterator for all pending events.

    Events are processed as the iterator is consumed.  Breaking out of, or
    discarding the iterator will leave the remaining events on the event queue.
    It is also safe to call this function inside of a loop that is already
    handling events (the event iterator is reentrant.)

    Example::

        for event in tcod.event.get():
            if event.type == "QUIT":
                print(event)
                raise SystemExit()
            elif event.type == "KEYDOWN":
                print(event)
            elif event.type == "MOUSEBUTTONDOWN":
                print(event)
            elif event.type == "MOUSEMOTION":
                print(event)
            else:
                print(event)
        # For loop exits after all current events are processed.
    """
    sdl_event = ffi.new("SDL_Event*")
    while lib.SDL_PollEvent(sdl_event):
        if sdl_event.type in _SDL_TO_CLASS_TABLE:
            yield _SDL_TO_CLASS_TABLE[sdl_event.type].from_sdl_event(sdl_event)
        else:
            yield Undefined.from_sdl_event(sdl_event)

class Event:
    """The base event class.

    Attributes:
        type (str): This events type.
        sdl_event: When available, this holds a python-cffi 'SDL_Event*'
                   pointer.  All sub-classes have this attribute.
    """

    def __init__(self, type: Optional[str] = None):
        if type is None:
            type = self.__class__.__name__.upper()
        self.type = type
        self.sdl_event = None

    @classmethod
    def from_sdl_event(cls, sdl_event: Any) -> Any:
        """Return a class instance from a python-cffi 'SDL_Event*' pointer."""
        raise NotImplementedError()


    def __str__(self) -> str:
        return "<type=%r>" % (self.type,)


class MouseState(Event):
    """
    Attributes:
        type (str): Always "MOUSESTATE".
        pixel (Point): The pixel coordinates of the mouse.
        tile (Point): The integer tile coordinates of the mouse on the screen.
        state (int): A bitmask of which mouse buttons are currently held.

            Will be a combination of the following names:

            * tcod.event.BUTTON_LMASK
            * tcod.event.BUTTON_MMASK
            * tcod.event.BUTTON_RMASK
            * tcod.event.BUTTON_X1MASK
            * tcod.event.BUTTON_X2MASK

    .. versionadded:: 9.3
    """

    def __init__(
        self,
        event: pygame.event,
        pixel: Tuple[int, int] = (0, 0),
        tile: Optional[Tuple[int, int]] = (0, 0),
        state: int = 0,
    ):
        #super().__init__()
        self.event = event
        self.pixel = Point(*pixel)
        self.__tile = Point(*tile) if tile is not None else None
        self.state = state

    @property
    def tile(self) -> Point:
        return _verify_tile_coordinates(self.__tile)

    @tile.setter
    def tile(self, xy: Tuple[int, int]) -> None:
        self.__tile = Point(*xy)

    def __repr__(self) -> str:
        return ("tcod.event.%s(pixel=%r, tile=%r, state=%s)") % (
            self.__class__.__name__,
            tuple(self.pixel),
            tuple(self.tile),
            _describe_bitmask(self.state, _REVERSE_BUTTON_MASK_TABLE_PREFIX),
        )

    def __str__(self) -> str:
        return ("<%s, pixel=(x=%i, y=%i), tile=(x=%i, y=%i), state=%s>") % (
            #super().__str__().strip("<>"),
            Event.__str__().strip("<>"),
            *self.pixel,
            *self.tile,
            _describe_bitmask(self.state, _REVERSE_BUTTON_MASK_TABLE),
        )


class EventDispatch(Generic[T]):

    def dispatch(self, event: Any) -> Optional[T]:
        """Send an event to an `ev_*` method.

        `*` will be the `event.type` attribute converted to lower-case.

        Values returned by `ev_*` calls will be returned by this function.
        This value always defaults to None for any non-overridden method.

        .. versionchanged:: 11.12
            Now returns the return value of `ev_*` methods.
            `event.type` values of None are deprecated.
        """
        if event.type is None:
            warnings.warn(
                "`event.type` attribute should not be None.",
                DeprecationWarning,
                stacklevel=2,
            )
            return None
        func = getattr(
            self, "ev_%s" % pygame.event.event_name(event.type).lower()
        )  # type: Callable[[Any], Optional[T]]
        return func(event)


    def event_get(self) -> None:
        for event in get():
            self.dispatch(event)

    def event_wait(self, timeout: Optional[float]) -> None:
        wait(timeout)
        self.event_get()

    def ev_quit(self, event: "tcod.event.Quit") -> Optional[T]:
        """Called when the termination of the program is requested."""


    def ev_keydown(self, event: pygame.KEYDOWN) -> Optional[T]:
        """Called when a keyboard key is pressed or repeated."""


    def ev_keyup(self, event: "tcod.event.KeyUp") -> Optional[T]:
        """Called when a keyboard key is released."""


    #def ev_mousemotion(self, event: "tcod.event.MouseMotion") -> Optional[T]:
    def ev_mousemotion(self, event: pygame.MOUSEMOTION) -> Optional[T]:
        """Called when the mouse is moved."""


    def ev_mousebuttondown(
        self, event: pygame.MOUSEBUTTONDOWN
    ) -> Optional[T]:
        """Called when a mouse button is pressed."""


    def ev_mousebuttonup(
        self, event: "tcod.event.MouseButtonUp"
    ) -> Optional[T]:
        """Called when a mouse button is released."""


    def ev_mousewheel(self, event: "tcod.event.MouseWheel") -> Optional[T]:
        """Called when the mouse wheel is scrolled."""


    def ev_textinput(self, event: "tcod.event.TextInput") -> Optional[T]:
        """Called to handle Unicode input."""


    def ev_windowshown(self, event: "tcod.event.WindowEvent") -> Optional[T]:
        """Called when the window is shown."""


    def ev_windowhidden(self, event: "tcod.event.WindowEvent") -> Optional[T]:
        """Called when the window is hidden."""


    def ev_windowexposed(self, event: "tcod.event.WindowEvent") -> Optional[T]:
        """Called when a window is exposed, and needs to be refreshed.

        This usually means a call to :any:`tcod.console_flush` is necessary.
        """


    def ev_windowmoved(self, event: "tcod.event.WindowMoved") -> Optional[T]:
        """Called when the window is moved."""


    def ev_windowresized(
        self, event: "tcod.event.WindowResized"
    ) -> Optional[T]:
        """Called when the window is resized."""


    def ev_windowsizechanged(
        self, event: "tcod.event.WindowResized"
    ) -> Optional[T]:
        """Called when the system or user changes the size of the window."""


    def ev_windowminimized(
        self, event: "tcod.event.WindowEvent"
    ) -> Optional[T]:
        """Called when the window is minimized."""


    def ev_windowmaximized(
        self, event: "tcod.event.WindowEvent"
    ) -> Optional[T]:
        """Called when the window is maximized."""


    def ev_windowrestored(
        self, event: "tcod.event.WindowEvent"
    ) -> Optional[T]:
        """Called when the window is restored."""


    def ev_windowenter(self, event: "tcod.event.WindowEvent") -> Optional[T]:
        """Called when the window gains mouse focus."""


    def ev_windowleave(self, event: "tcod.event.WindowEvent") -> Optional[T]:
        """Called when the window loses mouse focus."""


    def ev_windowfocusgained(
        self, event: "tcod.event.WindowEvent"
    ) -> Optional[T]:
        """Called when the window gains keyboard focus."""


    def ev_windowfocuslost(
        self, event: "tcod.event.WindowEvent"
    ) -> Optional[T]:
        """Called when the window loses keyboard focus."""


    def ev_windowclose(self, event: "tcod.event.WindowEvent") -> Optional[T]:
        """Called when the window manager requests the window to be closed."""


    def ev_windowtakefocus(
        self, event: "tcod.event.WindowEvent"
    ) -> Optional[T]:
        pass

    def ev_windowhittest(self, event: "tcod.event.WindowEvent") -> Optional[T]:
        pass

    def ev_(self, event: Any) -> Optional[T]:
        pass

    def ev_audiodeviceadd(self, event: Any) -> Optional[T]:
        pass



def get_mouse_state() -> MouseState:
    """Return the current state of the mouse.

    .. versionadded:: 9.3
    """
    xy = ffi.new("int[2]")
    buttons = lib.SDL_GetMouseState(xy, xy + 1)
    tile = _pixel_to_tile(*xy)
    if tile is None:
        return MouseState((xy[0], xy[1]), None, buttons)
    return MouseState((xy[0], xy[1]), (int(tile[0]), int(tile[1])), buttons)
