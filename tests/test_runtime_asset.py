from sgsl.parser import parse_text
from sgsl.renderers.html_renderer import render as render_html
from sgsl.renderers.roblox_renderer import render as render_roblox
from sgsl.renderers.glb_renderer import write as write_glb
import json


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


def test_asset_declaration_uses_runtime_asset_pipeline_and_html_placeholder():
    scene = parse_text(
        '''
scene ExternalAssetPreview

asset TownFountain
    robloxName "TownFountain"
    robloxId 123456789
    bounds 8 5 8

instance TownFountain Fountain01
    at 1 2 3
    rotate 0 45 0
    scale 1.2
'''
    )

    placement = scene["objects"][0]
    assert placement["name"] == "Fountain01"
    assert placement["asset"] == "TownFountain"
    assert placement["asset_symbol"] == "TownFountain"
    assert placement["roblox_name"] == "TownFountain"
    assert placement["roblox_id"] == 123456789
    assert placement["bounds"] == [8.0, 5.0, 8.0]

    html_object = render_html(scene)["objects"][0]
    assert html_object["type"] == "runtime_asset"
    assert html_object["bounds"] == [8.0, 5.0, 8.0]
    assert html_object["position"] == [1.0, 2.0, 3.0]

    output = render_roblox(scene, mode="module")
    assert "RuntimeAssetWorldPivot" not in output
    assert "Vector3.new(8.0, 5.0, 8.0)" in output
    assert "'TownFountain', 123456789.0" in output


def test_glb_writes_shared_runtime_asset_manifest(tmp_path):
    scene = parse_text(
        '''
scene RuntimeAssetManifest

asset Oak
    robloxName "OakTree01"
    bounds 5 11 5

instance Oak Tree01
    at 10 0 20
'''
    )
    output = write_glb(scene, tmp_path / "scene.glb")
    manifest = json.loads(output.with_suffix(".manifest.json").read_text(encoding="utf-8"))

    assert manifest["version"] == 1
    assert manifest["scene"] == "RuntimeAssetManifest"
    assert manifest["runtimeAssets"][0]["asset"] == "OakTree01"
    assert manifest["runtimeAssets"][0]["bounds"] == [5.0, 11.0, 5.0]


ANCHOR_SOURCE_TEMPLATE = """
scene AnchoredAsset

asset TownFountain
    robloxName "Water fountain"
    robloxId 123456789
    bounds 8 5 8

instance Fountain01 TownFountain
    at 10 0 -4
    scale 2
{anchor}
"""


def _anchored(anchor: str | None):
    line = f"    anchor {anchor}" if anchor else ""
    scene = parse_text(ANCHOR_SOURCE_TEMPLATE.format(anchor=line))
    return scene["objects"][0]


def test_asset_instance_defaults_to_the_centre_it_always_used():
    # The default has to stay bit-for-bit what it was, because every existing
    # placement in every scene relies on it.
    assert _anchored(None)["position"] == [10.0, 0.0, -4.0]
    assert _anchored("center center center")["position"] == [10.0, 0.0, -4.0]


def test_asset_instance_anchor_bottom_lifts_by_half_its_scaled_height():
    # An `asset` is resolved onto the imported Model's pivot, and a Roblox
    # Model with no PrimaryPart pivots about its bounding box centre - so
    # without this the bottom half of the model stands underground.
    # bounds Y 5 * scale 2 / 2 = 5.
    assert _anchored("center bottom center")["position"] == [10.0, 5.0, -4.0]
    assert _anchored("center top center")["position"] == [10.0, -5.0, -4.0]


def test_asset_instance_anchors_on_every_axis():
    # bounds X and Z are 8, scale 2, so half is 8 on both.
    assert _anchored("left center center")["position"] == [18.0, 0.0, -4.0]
    assert _anchored("right center center")["position"] == [2.0, 0.0, -4.0]
    assert _anchored("center center front")["position"] == [10.0, 0.0, 4.0]
    assert _anchored("center center back")["position"] == [10.0, 0.0, -12.0]


def test_asset_instance_anchor_composes_with_an_enclosing_scale():
    # The offset is expressed in the parent's frame, so the parent transform
    # scales it afterwards: 5 (own) * 3 (parent) = 15, on top of the parent's
    # own scaling of the instance position.
    scene = parse_text(
        """
scene NestedAnchoredAsset

asset TownFountain
    robloxName "Water fountain"
    bounds 8 5 8

component Square
    instance Fountain TownFountain
        at 0 0 0
        scale 2
        anchor center bottom center

instance Square Plaza
    at 0 0 0
    scale 3
"""
    )
    placement = scene["objects"][0]
    assert placement["position"] == [0.0, 15.0, 0.0]
    assert placement["scale"] == 6.0


def test_anchor_on_a_plain_component_instance_is_refused():
    # A component is a subtree of primitives that are each anchored on their
    # own terms; there is no single box to measure, so the same word would
    # quietly mean something else than it does on a block.
    import pytest

    with pytest.raises(Exception) as excinfo:
        parse_text(
            """
scene AnchoredComponent

component Box
    block Body
        at 0 0 0
        size 2 2 2
        color gray

instance Box Box01
    at 0 0 0
    anchor center bottom center
"""
        )
    assert "only supported on instances of an `asset`" in str(excinfo.value)


def test_asset_instance_rejects_an_unknown_anchor_word():
    import pytest

    with pytest.raises(Exception) as excinfo:
        _anchored("center middle center")
    assert "invalid Y anchor" in str(excinfo.value)
