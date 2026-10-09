from dataclasses import replace

from quarry.blockout import Blockout, Landmark, Path, Reason, Zone
from quarry.carry import touched

AI = Reason("ai", "test")


def zone(name, x, radius=20):
    return Zone(name, (x, 100), radius, 10, "dome", "add", AI)


def layout(*zones, landmarks=(), paths=()):
    return Blockout(landmarks=landmarks, paths=paths, zones=zones)


def edited(blockout, name, **values):
    return replace(blockout, zones=tuple(replace(z, **values) if z.name == name else z for z in blockout.zones))


def test_nothing_is_touched_when_nothing_changed():
    old = layout(zone("hill", 50), zone("lake", 150))

    assert touched(old, old) == set()


def test_a_moved_zone_touches_what_it_left_and_what_it_reached():
    # hill sits against left; moved right, it leaves left and reaches right
    old = layout(zone("left", 20), zone("hill", 55), zone("right", 120), zone("far", 300))

    new = edited(old, "hill", center=(95, 100))

    assert touched(old, new) == {"hill", "left", "right"}


def test_a_resized_zone_touches_what_its_larger_shape_overlaps():
    old = layout(zone("hill", 50), zone("lake", 100), zone("far", 300))

    new = edited(old, "hill", radius=40)

    assert touched(old, new) == {"hill", "lake"}


def test_an_overlap_gained_touches_the_zone_reached():
    old = layout(zone("hill", 50), zone("lake", 120))

    new = edited(old, "hill", radius=55)  # now reaches 105, inside the lake's 100–140

    assert touched(old, new) == {"hill", "lake"}


def test_an_overlap_lost_still_touches_the_zone_left_behind():
    old = layout(zone("hill", 50, radius=55), zone("lake", 120))

    new = edited(old, "hill", radius=20)  # once reached into the lake, no longer does

    assert touched(old, new) == {"hill", "lake"}


def test_a_height_change_touches_only_the_zone_and_its_neighbours():
    old = layout(zone("hill", 50), zone("knoll", 80), zone("far", 300))

    new = edited(old, "hill", height=25)

    assert touched(old, new) == {"hill", "knoll"}


def test_a_restacked_zone_counts_as_edited():
    old = layout(zone("hill", 50), zone("lake", 80), zone("far", 300))

    new = replace(old, zones=(old.zones[1], old.zones[0], old.zones[2]))

    assert touched(old, new) == {"hill", "lake"}


def test_a_removed_zone_touches_what_it_overlapped():
    old = layout(zone("hill", 50), zone("lake", 80), zone("far", 300))

    new = replace(old, zones=(old.zones[1], old.zones[2]))

    assert touched(old, new) == {"lake"}


CAMP, SUMMIT = Landmark("camp", (100, 10), AI), Landmark("summit", (100, 190), AI)


def trail(*points, width=8):
    return Path("camp", "summit", points, AI, cut=True, width=width)


def test_a_cut_path_is_touched_by_an_edited_zone_its_strip_crosses():
    old = layout(zone("hill", 60), landmarks=(CAMP, SUMMIT), paths=(trail((100, 10), (100, 190)),))

    reached = edited(old, "hill", radius=40)  # 20–100: the strip's edge is at 96
    short = edited(old, "hill", radius=30)  # 30–90: still clear of it

    assert touched(old, reached) == {"hill", "camp→summit"}
    assert touched(old, short) == {"hill"}


def test_an_edited_cut_path_touches_the_zones_under_its_old_and_new_strip():
    old = layout(
        zone("west", 40), zone("east", 160), zone("far", 400),
        landmarks=(CAMP, SUMMIT), paths=(trail((100, 10), (60, 100), (100, 190)),),
    )

    rerouted = replace(old, paths=(trail((100, 10), (140, 100), (100, 190)),))

    assert touched(old, rerouted) == {"camp→summit", "west", "east"}


def test_a_moved_landmark_touches_the_zones_under_its_old_and_new_pad():
    old = layout(zone("hill", 50), zone("lake", 150), zone("far", 400), landmarks=(Landmark("camp", (70, 100), AI),))

    moved = replace(old, landmarks=(Landmark("camp", (125, 100), AI),))

    assert touched(old, moved) == {"hill", "lake"}
