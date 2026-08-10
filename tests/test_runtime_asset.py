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
