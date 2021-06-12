# -----------------------------------------------------------------------------
# elevator.py
#
# Certain problems often involve the implementation of "state
# machines."  For example, consider the operation of an elevator.  At
# any given moment, the elevator is in a certain "operational state".
# For example, it's positioned at a given floor and it's either
# idle, loading passengers, or moving. The doors are open or closed.
# The elevator transitions between states according to various events
# which may include buttons, sensors, and timers.
#
# Suppose that you are tasked with designing and writing the control
# software for an elevator in a 5-floor building.   The elevator has
# the following inputs:
#
#  1. A push button inside the elevator to select a destination floor.
#  2. Two push buttons (up/down) on each floor to request the elevator.
#  3. A sensor on each floor to indicate the current elevator position
#     (triggered when the elevator reaches a given floor).
#  4. A time-expired event that's used for time-related operation.
#
# The elevator has the following control outputs:
#
#  1. Hoist motor control (controls up/down motion)
#  2. Door motor control (controls door open/close motion)
#  3. Set a timer.
#
# The elevator operates in three primary operational modes.
#
# 1. IDLE: The elevator remains still if there are no floor requests.
#    This means it's just stopped on whatever floor it happened to
#    go to last with the doors closed.  Any request causes
#    the elevator to start moving towards that floor.
#
# 2. MOVING: The elevator is in motion. Once in motion, the
#    elevator continues to move in its current direction until
#    it reaches the highest or lowest requested floor.  Along
#    the way, the elevator will serve other requests as appropriate.
#    For example, suppose the elevator is on floor 1 and someone
#    hits the "down" button on floor 4.  The elevator will start
#    moving up.  If, on the way up, someone presses "up" on
#    floor 3, the elevator will stop and load passengers before
#    continuing up to floor 4.  If someone also pressed "down" on
#    floor 5, the elevator would *pass* floor 4 and go up to
#    floor 5 first.  It would then stop on floor 4 on its way
#    back down.
#
# 3. LOADING: When stopped at a floor, the door opens for 10 seconds
#    and then closes again.  There is no mechanism to make the door
#    stay open.  Anything in the way gets cut in half--an obvious
#    limitation to be addressed in a future version.
#
# YOUR TASK: Design and implement code for the internal logic and
# control of the elevator.  Come up with some strategy for testing it.
#
# CHALLENGE: To write this code you might ask to know more about how
# the elevator control actually works (i.e., How are inputs delivered?
# How is data encoded?  How are commands issued to the motors?). How
# does the elevator deal with acceleration and deceleration. However,
# you're not going to get it. That's a different corporate division.
# So, you've got to figure out how to implement the elevator control
# software without any first-hand knowledge of its deployment
# environment or the laws of physics.  Naturally, the lack of
# information means that your implementation will need to be
# extended/embedded in some other software (not shown/provided) to be
# used in the real world.  It also means that your understanding
# of the problem might be incomplete--you should write the code
# in anticipation of new unforeseen "requirements."
# -----------------------------------------------------------------------------

# A Hint: It might make sense to separate the problem into separate
# concerns.  For example, perhaps you define an "Elevator" class that
# deals with the logic of the elevator and a "ElevatorControl" class
# that is focused on its interaction with "real" world elements.  For
# example:

import copy
import random
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from typing import List


class Direction(Enum):
    NONE = 1
    UP = 2
    DOWN = 3


class DoorMotion(Enum):
    NONE = 1
    OPEN = 2
    CLOSE = 3


class ControlOutput(ABC):
    pass


@dataclass
class HoistMotor(ControlOutput):
    direction: Direction


class StopMotor(ControlOutput):
    pass


@dataclass
class DoorMotor(ControlOutput):
    motion: DoorMotion


@dataclass
class SetTimer(ControlOutput):
    pass


class Event(ABC):
    pass


@dataclass
class DestinationFloorSelected(Event):
    destination_floor: int


@dataclass
class RequestButtonPressed(Event):
    floor: int
    direction: Direction


@dataclass
class ReachedFloor(Event):
    floor: int


class TimerExpired(Event):
    pass


class State(ABC):
    def __init__(self, elevator):
        self._elevator = elevator

    def _unsupported_event(self, event):
        raise RuntimeError(f"Unsupported event:{event} in state {self}")

    def _new_state(self, state_cls):
        return state_cls(elevator=self._elevator)

    def __repr__(self):
        return f"{type(self).__name__}"

    # handles the event and returns HandleEventResult
    def handle_event(self, event: Event):
        pass


class Idle(State):
    def handle_event(self, event):
        assert not self._elevator.destinations
        assert self._elevator.going_direction == Direction.NONE

        if isinstance(event, RequestButtonPressed):
            # if current floor has a request, just opens the door
            if event.floor == self._elevator.current_floor:
                return HandleEventResult(
                    next_state=Loading(elevator=self._elevator),
                    control_output=[SetTimer()],
                )
            else:
                # TODO: this is simplified, as soon as one request of elevator
                # is pressed, the elevator starts moving.
                self._elevator.receive_request(event)
                return HandleEventResult(
                    next_state=Moving(elevator=self._elevator),
                    control_output=[
                        HoistMotor(direction=self._elevator.going_direction)
                    ],
                )
        elif isinstance(event, DestinationFloorSelected):
            if event.destination_floor == self._elevator.current_floor:
                # print(f"Passenger, you are already at floor: {event.destination_floor}")
                # TODO: maybe reset the timer?
                return HandleEventResult(
                    next_state=Loading(elevator=self._elevator),
                    control_output=[DoorMotor(motion=DoorMotion.OPEN), SetTimer()],
                )
            else:
                self._elevator.receive_destination(event.destination_floor)
                return HandleEventResult(
                    next_state=Moving(elevator=self._elevator),
                    control_output=[
                        HoistMotor(direction=self._elevator.going_direction)
                    ],
                )
        else:
            self._unsupported_event(event)


class Moving(State):
    def handle_event(self, event):
        if isinstance(event, ReachedFloor):
            need_to_open_door = self._elevator.reach_floor(event.floor)
            if need_to_open_door:
                return HandleEventResult(
                    next_state=Loading(elevator=self._elevator),
                    control_output=[
                        StopMotor(),
                        DoorMotor(motion=DoorMotion.OPEN),
                        SetTimer(),
                    ],
                )
            else:
                return HandleEventResult(
                    next_state=Moving(elevator=self._elevator),
                    control_output=[
                        HoistMotor(direction=self._elevator.going_direction)
                    ],
                )
        elif isinstance(event, DestinationFloorSelected):
            # notice a moving elevator will not stop when the current floor is pressed
            self._elevator.receive_destination(event.destination_floor)
            return HandleEventResult(
                next_state=Moving(elevator=self._elevator),
                control_output=[HoistMotor(direction=self._elevator.going_direction)],
            )
        elif isinstance(event, RequestButtonPressed):
            # elevator is moving, cannot stop immediately, so only record the request
            self._elevator.receive_request(event)
            return HandleEventResult(
                next_state=Moving(elevator=self._elevator),
                control_output=[HoistMotor(direction=self._elevator.going_direction)],
            )
        else:
            self._unsupported_event(event)


class Loading(State):
    def handle_event(self, event):
        if isinstance(event, DestinationFloorSelected):
            if event.destination_floor == self._elevator.current_floor:
                # if the door is open and passenger pressed current, keep the door open
                # this passenger is confused.
                # print(f"Passenger, you are already at floor: {event.destination_floor}")
                # TODO: maybe reset the timer?
                pass
            else:
                self._elevator.receive_destination(event.destination_floor)
            return HandleEventResult(
                next_state=Loading(elevator=self._elevator), control_output=[]
            )
        elif isinstance(event, RequestButtonPressed):
            # elevator door is open, just record the request
            self._elevator.receive_request(event)
            return HandleEventResult(
                next_state=Loading(elevator=self._elevator), control_output=[]
            )
        elif isinstance(event, TimerExpired):
            # time to close the door
            need_to_move = self._elevator.close_door()
            if need_to_move:
                return HandleEventResult(
                    next_state=Moving(elevator=self._elevator),
                    control_output=[
                        DoorMotor(motion=DoorMotion.CLOSE),
                        HoistMotor(direction=self._elevator.going_direction),
                    ],
                )
            else:
                return HandleEventResult(
                    next_state=Idle(elevator=self._elevator),
                    control_output=[DoorMotor(motion=DoorMotion.CLOSE)],
                )
        else:
            self._unsupported_event(event)


@dataclass
class HandleEventResult:
    next_state: State
    control_output: List[ControlOutput] = field(default_factory=list)


class Elevator:
    _MIN_FLOOR = 1
    _MAX_FLOOR = 5

    def __init__(self, initial_floor, control):
        self._state = Idle(self)
        self._current_floor = initial_floor
        self._control = control
        self._going_direction = Direction.NONE
        self._destinations = set()
        self._up_requests = set()
        self._down_requests = set()

    def _as_tuple(self):
        return (
            type(self._state),
            self._current_floor,
            self._going_direction,
            self._destinations,
            self._up_requests,
            self._down_requests,
        )

    def __eq__(self, other):
        return self._as_tuple() == other._as_tuple()

    def __hash__(self):
        return hash(
            (
                type(self._state),
                self._current_floor,
                self._going_direction,
                frozenset(self._destinations),
                frozenset(self._up_requests),
                frozenset(self._down_requests),
            )
        )

    @property
    def current_floor(self):
        return self._current_floor

    @property
    def destinations(self):
        return self._destinations

    @property
    def going_direction(self):
        return self._going_direction

    def _count_higher_floors(self, floor_set):
        # returns the number of floors that are higher than current floor in the floor_set
        return sum(1 for floor in floor_set if floor >= self._current_floor)

    def _count_lower_floors(self, floor_set):
        # returns the number of floors that are lower than current floor in the floor_set
        return sum(1 for floor in floor_set if floor <= self._current_floor)

    def _get_direction_with_floor_set(self, floor_set):
        # returns Direction.UP if more floors in the floor_set is on the upper floors
        # compared to current floor
        return (
            Direction.UP
            if self._count_higher_floors(floor_set) > len(floor_set) // 2
            else Direction.DOWN
        )

    def _update_direction(self):
        # Notice current_floor can still be in self._destinations as it might have been
        # just added by a passenger pressing the current floor while the elevator is moving
        # assert self._current_floor not in self._destinations

        # next direction is purely a function of current going direction,
        # any outstanding destinations and any outstanding requests
        if not any([self._destinations, self._up_requests, self._down_requests]):
            next_direction = Direction.NONE
        elif self._current_floor == Elevator._MIN_FLOOR:
            # assert self._count_lower_floors(self._destinations) == 0
            next_direction = Direction.UP
        elif self._current_floor == Elevator._MAX_FLOOR:
            # assert self._count_higher_floors(self._destinations) == 0
            next_direction = Direction.DOWN

        # elevator prioritize unloading current passengers over picking up
        # new ones.
        elif self._going_direction == Direction.NONE:
            if self._destinations:
                next_direction = self._get_direction_with_floor_set(self._destinations)
            else:
                next_direction = self._get_direction_with_floor_set(
                    self._up_requests.union(self._down_requests)
                )
        elif self._going_direction == Direction.UP:
            # elevator is going up, so it will keep going up unless there is no need to go up.
            if self._count_higher_floors(self._destinations) > 0:
                next_direction = Direction.UP
            elif (
                self._count_higher_floors(self._up_requests.union(self._down_requests))
                > 0
            ):
                next_direction = Direction.UP
            else:
                next_direction = Direction.DOWN
        else:
            # elevator is going down, so it will keep going down unless there is no need to go down.
            if self._count_lower_floors(self._destinations) > 0:
                next_direction = Direction.DOWN
            elif (
                self._count_lower_floors(self._up_requests.union(self._down_requests))
                > 0
            ):
                next_direction = Direction.DOWN
            else:
                next_direction = Direction.UP

        old_direction = self._going_direction
        if old_direction != next_direction:
            # print(f"Updating direction from {old_direction} to {next_direction}")
            pass
        self._going_direction = next_direction

    # returns True if needs to open door for loading or unloading
    def reach_floor(self, floor):
        assert floor >= Elevator._MIN_FLOOR and floor <= Elevator._MAX_FLOOR
        assert self._going_direction != Direction.NONE
        # print(f"Elevator reached floor: {floor}")
        previous_floor = self._current_floor
        self._current_floor = floor
        assert abs(previous_floor - self._current_floor) == 1
        result = False
        if floor in self._destinations:
            self._destinations.remove(floor)
            result = True
        # pick up passengers along the right direction
        if floor in self._up_requests and self._going_direction == Direction.UP:
            self._up_requests.remove(floor)
            result = True
        if floor in self._down_requests and self._going_direction == Direction.DOWN:
            self._down_requests.remove(floor)
            result = True
        self._update_direction()
        return result

    # Returns True if the elevator needs to move again
    def close_door(self):
        # print(f"Elevator door closed at floor:{self._current_floor}")
        self._update_direction()
        return False if self._going_direction == Direction.NONE else True

    def receive_request(self, request: RequestButtonPressed):
        assert not (
            request.floor == Elevator._MIN_FLOOR and request.direction == Direction.DOWN
        )
        assert not (
            request.floor == Elevator._MAX_FLOOR and request.direction == Direction.UP
        )
        if request.direction == Direction.UP:
            self._up_requests.add(request.floor)
        else:
            self._down_requests.add(request.floor)
        self._update_direction()

    def receive_destination(self, floor):
        self._destinations.add(floor)
        self._update_direction()

    def handle_event(self, event):
        # print()
        # print(f"Elevator:{self}@floor{self._current_floor} received event:{event}")
        result = self._state.handle_event(event)
        self._state = result.next_state
        self._control.handle_control_output(result.control_output)

    def validate(self):
        assert not (
            self._current_floor == Elevator._MIN_FLOOR
            and self._going_direction == Direction.DOWN
        )

        assert not (
            self._current_floor == Elevator._MAX_FLOOR
            and self._going_direction == Direction.UP
        )

        assert not (
            isinstance(self._state, Idle) and self._going_direction != Direction.NONE
        )

    def __repr__(self):
        return f"Elevator(state:{self._state}, current_floor:{self._current_floor}, going_direction:{self._going_direction}, destinations: {self._destinations}, up_requests:{self._up_requests}, down_requests:{self._down_requests})"


# Class for implementing "elevator" commands.
# One challenge: We don't know anything about the actual elevator.
# So, what do you put here?


class ElevatorControl:
    def __init__(self, queit=False):
        self._queit = queit

    def _print(self, msg):
        if self._queit:
            return

    def handle_control_output(self, commands: List[ControlOutput]):
        for command in commands:
            if isinstance(command, HoistMotor):
                assert command.direction != Direction.NONE
                self._print(f"Running motor {command.direction}")
            elif isinstance(command, DoorMotor):
                assert command.motion != DoorMotion.NONE
                self._print(f"Door motion {command.motion}")
            elif isinstance(command, StopMotor):
                self._print(f"Stop motor")
            elif isinstance(command, SetTimer):
                self._print(f"StartTimer")
            else:
                raise RuntimeError(f"Unsupported control command: {command}")


class Simulator:
    def __init__(self, elevator, control, events):
        self._elevator = elevator
        self._control = control
        self._events = deque(events)

    def run(self):
        assert isinstance(self._elevator._state, Idle)
        for event, (state, floor) in self._events:
            print(f"Received event:{event}")
            self._elevator.handle_event(event)
            print(elevator)
            assert isinstance(self._elevator._state, state)
            assert floor == self._elevator._current_floor
            print()

    @staticmethod
    def simulate():
        def do_it():
            return random.choice([0, 1]) == 0

        def get_next_elevator(elev):
            next_elev = set()

            # all destination buttons pressed
            for floor in range(Elevator._MIN_FLOOR, Elevator._MAX_FLOOR + 1):
                new_elev = copy.deepcopy(elev)
                new_elev.handle_event(DestinationFloorSelected(destination_floor=floor))
                next_elev.add(new_elev)

            # all up buttons
            for floor in range(Elevator._MIN_FLOOR, Elevator._MAX_FLOOR):
                new_elev = copy.deepcopy(elev)
                new_elev.handle_event(
                    RequestButtonPressed(floor=floor, direction=Direction.UP)
                )
                next_elev.add(new_elev)

            # all down buttons
            for floor in range(Elevator._MIN_FLOOR + 1, Elevator._MAX_FLOOR + 1):
                new_elev = copy.deepcopy(elev)
                new_elev.handle_event(
                    RequestButtonPressed(floor=floor, direction=Direction.DOWN)
                )
                next_elev.add(new_elev)

            # simulate motion
            if isinstance(elev._state, Moving):
                assert elev._going_direction != Direction.NONE

            if (
                isinstance(elev._state, Moving)
                and elev._going_direction == Direction.UP
            ):
                new_elev = copy.deepcopy(elev)
                new_elev.handle_event(ReachedFloor(floor=elev._current_floor + 1))
                next_elev.add(new_elev)

            if (
                isinstance(elev._state, Moving)
                and elev._going_direction == Direction.DOWN
            ):
                new_elev = copy.deepcopy(elev)
                new_elev.handle_event(ReachedFloor(floor=elev._current_floor - 1))
                next_elev.add(new_elev)

            # simulate door close
            if isinstance(elev._state, Loading) and do_it():
                new_elev = copy.deepcopy(elev)
                new_elev.handle_event(TimerExpired())
                next_elev.add(new_elev)

            if not next_elev:
                raise RuntimeError(f"Deadlock detected: {elev}")
            return next_elev

        control = ElevatorControl(queit=True)
        to_check = deque([Elevator(1, control)])
        seen = set()
        while to_check:
            elev = to_check.popleft()
            elev.validate()
            next_elevs = get_next_elevator(elev)
            for e in next_elevs:
                if e not in seen:
                    to_check.append(e)
                    seen.add(e)
            print(f"to_check: {len(to_check)}, seen: {len(seen)}")
        # print(seen)


# -----------------------------------------------------------------------------
# Testing
#
# How do you test something like this?  See the file testing.py when you're
# ready.
control = ElevatorControl()
elevator = Elevator(1, control)


def pickup_at_multiple_floors():
    events = [
        (RequestButtonPressed(floor=2, direction=Direction.UP), (Moving, 1)),
        (ReachedFloor(floor=2), (Loading, 2)),
        (TimerExpired(), (Idle, 2)),
        (DestinationFloorSelected(destination_floor=5), (Moving, 2)),
        (RequestButtonPressed(floor=4, direction=Direction.UP), (Moving, 2)),
        (ReachedFloor(floor=3), (Moving, 3)),
        (ReachedFloor(floor=4), (Loading, 4)),
        (TimerExpired(), (Moving, 4)),
        (DestinationFloorSelected(destination_floor=5), (Moving, 4)),
        (ReachedFloor(floor=5), (Loading, 5)),
        (TimerExpired(), (Idle, 5)),
    ]

    Simulator(elevator, control, events).run()


# pickup_at_multiple_floors()

Simulator.simulate()
