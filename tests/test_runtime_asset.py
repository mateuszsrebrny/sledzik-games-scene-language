from sgsl.parser import parse_text
from sgsl.renderers.html_renderer import render as render_html
from sgsl.renderers.roblox_renderer import render as render_roblox


SOURCE = """
scene RuntimeAssetPreview

component Pump
    runtime_asset Pump

    block Base
        at 0 0 0
        size 2 1 2
        color gray

instance Pump01 Pump
    at 0 0 0
"""


def test_runtime_asset_is_kept_in_html_preview():
    scene = parse_text(SOURCE)

    assert len(render_html(scene)["objects"]) == 1


def test_runtime_asset_is_omitted_from_roblox_part_output():
    scene = parse_text(SOURCE)

    output = render_roblox(scene, mode="module")

    assert "Builder.makeBlock" not in output
    assert "Builder.makeRuntimeAssetMarker" in output
    assert "'Pump01', 'Pump'" in output


def test_runtime_asset_marker_preserves_nested_instance_transform():
    scene = parse_text(
        """
scene RuntimeAssetTransformPreview

component House
    runtime_asset HouseGardenRed

    block Body
        at 0 1 0
        size 2 2 2
        color red

component Row
    instance Home House
        at 12 3 -4
        rotate 0 90 0
        scale 1.5

instance Neighborhood Row
    at 10 0 2
"""
    )

    placement = next(obj for obj in scene["objects"] if obj["type"] == "runtime_asset_instance")
    assert placement["name"] == "Neighborhood.Home"
    assert placement["asset"] == "HouseGardenRed"
    assert placement["position"] == [22.0, 3.0, -2.0]
    assert placement["rotation"] == [0.0, 90.0, 0.0]
    assert placement["scale"] == 1.5

    html = render_html(scene)
    assert len(html["objects"]) == 1
