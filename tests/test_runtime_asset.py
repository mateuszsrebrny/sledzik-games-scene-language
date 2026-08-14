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
