#  ------------------------------------------------------------------------------------------
#  Copyright (c) Microsoft Corporation. All rights reserved.
#  Licensed under the MIT License (MIT). See LICENSE in the repo root for license information.
#  ------------------------------------------------------------------------------------------
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import pytest
import numpy as np
from passthrough_model import make_distance_range, make_stroke_rectangle, \
    make_fill_rectangle, make_nesting_rectangles
from score import convert_rgb_colour_to_hex

rgb_colour_testdata = [
    (0x00, 0x00, 0x00, "000000"),
    (0x0f, 0x00, 0x00, "0F0000"),
    (0xff, 0x00, 0x00, "FF0000"),
    (0x00, 0x0f, 0x00, "000F00"),
    (0x00, 0xff, 0x00, "00FF00"),
    (0x00, 0x00, 0x0f, "00000F"),
    (0x00, 0x00, 0xff, "0000FF"),
    (0x04, 0x08, 0x0a, "04080A"),
    (0xf4, 0xf8, 0xfa, "F4F8FA")
]


@pytest.mark.parametrize("red,green,blue,colour", rgb_colour_testdata)
def test_convert_rgb_colour_to_hex(red: int, green: int, blue: int, colour: str) -> None:
    """
    Test that config colours, which are TupleInt3's, can be formatted as
    strings.

    :param red: Red component.
    :param green: Green component.
    :param blue: Blue component.
    :param colour: Expected hex string.
    """
    assert convert_rgb_colour_to_hex((red, green, blue)) == colour


# Test data for test_make_distance_range
make_distance_range_test_data: List[List[int]] = [
    [],
    [0],
    [0, 0],
    [1, 0, 1],
    [1, 0, 0, 1],
    [2, 1, 0, 1, 2],
    [2, 1, 0, 0, 1, 2],
    [3, 2, 1, 0, 1, 2, 3],
    [3, 2, 1, 0, 0, 1, 2, 3],
    [4, 3, 2, 1, 0, 1, 2, 3, 4],
]


@pytest.mark.parametrize("expected", make_distance_range_test_data)
def test_make_distance_range(expected: List[int]) -> None:
    """
    Test make_distance_range.

    :param expected: Expected range.
    """
    length = len(expected)
    actual = make_distance_range(length)
    assert actual.shape == (length,)
    expected_array = np.asarray(expected, dtype=np.int64)
    assert np.array_equal(actual, expected_array)


@dataclass(frozen=True)
class RectInRectRayData:
    """
    Contains information about points on a ray through a rectangle containing another
    stroked or filled rectangle.

    Note that all coordinates are clamped to a minimum of 0 so they can be used
    as indices into numpy arrays.
    """
    first_start: int  # Coordinate where the inner rectangle starts (fill or stroke).
    first_end: int  # Coordinate where the first stroke of the inner rectangle ends.
    second_start: int  # Coordinate where the second stroke of the inner rectange starts.
    second_end: int  # Coordinate where the inner rectangle ends (fill or stroke).

    @staticmethod
    def create(dim: int, half_side: int, thickness: int) -> RectInRectRayData:
        """
        Given a dimension, half side length and thickness, create RectInRectRayData.

        :param dim: Outer rectangle dimension.
        :param half_side: Inner rectangle approximate half side length.
        :param thickness: Stroke thickness.
        :return: RectInRectRayData.
        """
        def _clamp_not_neg(x: int) -> int:
            """
            Make sure an int isn't -ve.

            :param i: int to test.
            :return: i or 0, whichever is greater.
            """
            return max(x, 0)
        fill_length = half_side * 2 if dim % 2 == 0 else half_side * 2 - 1
        first_start = int((dim - fill_length) / 2)
        first_end = first_start + thickness
        second_end = first_start + fill_length
        second_start = second_end - thickness
        return RectInRectRayData(_clamp_not_neg(first_start), _clamp_not_neg(first_end),
                                 _clamp_not_neg(second_start), _clamp_not_neg(second_end))


def make_stroke_rectangle_alt(dim0: int, dim1: int, half_side: int, thickness: int, fill: bool) -> np.array:
    """
    Create filled or stroked rectangle in rectangle.

    :param fill: True for filled inner rectangle, false for stroked inner rectangle.
    :return: 2d np.array representing a rectangle in a rectangle.
    """
    dim0_data = RectInRectRayData.create(dim0, half_side, thickness)
    dim1_data = RectInRectRayData.create(dim1, half_side, thickness)

    rows = np.zeros((dim0, dim1), dtype=np.int64)
    rows[dim0_data.first_start:dim0_data.second_end,
         dim1_data.first_start:dim1_data.second_end] = 1
    if not fill:
        rows[dim0_data.first_end:dim0_data.second_start,
             dim1_data.first_end:dim1_data.second_start] = 0
    return rows


def test_make_fill_rectangle() -> None:
    """
    Test make_fill_rectangle.
    """
    for dim0 in range(1, 30):
        for dim1 in range(1, 30):
            for half_side in range(max(dim0, dim1) + 1):
                filled = make_fill_rectangle(dim0, dim1, half_side)
                assert filled.shape == (dim0, dim1)
                filled_alt = make_stroke_rectangle_alt(dim0, dim1, half_side, 1, True)
                assert np.array_equal(filled, filled_alt)


def test_make_stroke_rectangle() -> None:
    """
    Test make_stroke_rectangle.
    """
    for dim0 in range(1, 30):
        for dim1 in range(1, 30):
            for half_side in range(max(dim0, dim1) + 1):
                for thickness in range(1, 5):
                    stroked = make_stroke_rectangle(dim0, dim1, half_side, thickness)
                    assert stroked.shape == (dim0, dim1)
                    stroked_alt = make_stroke_rectangle_alt(dim0, dim1, half_side, thickness, False)
                    assert np.array_equal(stroked, stroked_alt)


make_nesting_rectangles_test_data: List[Tuple[int, int, int]] = [
    (1, 20, 30),
    (2, 20, 30),
    (3, 20, 30),
    (10, 20, 30),
    (20, 30, 20),
    (30, 30, 20),
]


@pytest.mark.parametrize("num_features,dim0,dim1", make_nesting_rectangles_test_data)
def test_make_nesting_rectangles(num_features: int, dim0: int, dim1: int) -> None:
    """
    Test make_nesting_rectangles.

    :param num_features: Number of rectangles.
    :param dim0: Target array dim0.
    :param dim1: Target array dim1.
    """
    for thickness in range(1, 5):
        nesting = make_nesting_rectangles(num_features, dim0, dim1, thickness)
        assert nesting.shape == (num_features, dim0, dim1)
        total = nesting.sum(axis=0)
        assert total.shape == (dim0, dim1)
        assert np.array_equal(total, np.ones((dim0, dim1)))