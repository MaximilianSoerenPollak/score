import pytest
import json
from pathlib import Path
from sphinx_needs.data import SphinxNeedsData
from sphinx.testing.util import SphinxTestApp


@pytest.fixture(scope="session")
def sphinx_base_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("sphinx")


@pytest.fixture(scope="session")
def sphinx_app_setup(sphinx_base_dir):
    def _create_app(conf_content, rst_content, requierments_text=None):
        src_dir = sphinx_base_dir / "src"
        src_dir.mkdir(exist_ok=True)

        (src_dir / "conf.py").write_text(conf_content)
        (src_dir / "index.rst").write_text(rst_content)
        (src_dir / "requierments.txt").write_text(json.dumps(requierments_text))

        app = SphinxTestApp(
            freshenv=True,
            srcdir=Path(src_dir),
            confdir=Path(src_dir),
            outdir=sphinx_base_dir / "out",
            buildername="html",
            warningiserror=True,
            confoverrides={"requirement_links": str(src_dir / "requierments.txt")},
        )

        return app

    return _create_app


@pytest.fixture(scope="session")
def basic_conf():
    return """
extensions = [
    "sphinx_needs",
    "score_source_code_linker",
]
needs_types = [
    dict(directive="test_req", title="Testing Requirement", prefix="TREQ_", color="#BFD8D2", style="node"),
]
needs_extra_options = ["source_code_link"]
needs_string_links = { 
    "source_code_linker": {
        "regex": r"(?P<value>[^,]+)",
        "link_url": "{{value}}",
        "link_name": "Source Code Link",
        "options": ["source_code_link"],
    },
}
"""


@pytest.fixture(scope="session")
def basic_needs():
    return """
TESTING SOURCE LINK 
===================

.. test_req:: TestReq1
   :id: TREQ_ID_1
   :status: valid

.. test_req:: TestReq2
   :id: TREQ_ID_2
   :status: open
"""


@pytest.fixture(scope="session")
def example_source_link_text_all_ok():
    return {
        "TREQ_ID_1": [
            "https://github.com/dependix/platform/blob/aacce4887ceea1f884135242a8c182db1447050/tools/sources/implementation1.py#L2",
            "https://github.com/dependix/platform/blob//tools/sources/implementation_2_new_file.py#L20",
        ],
        "TREQ_ID_2": [
            "https://github.com/dependix/platform/blob/f53f50a0ab1186329292e6b28b8e6c93b37ea41/tools/sources/implementation1.py#L18"
        ],
    }


@pytest.fixture(scope="session")
def example_source_link_text_non_existent():
    return {
        "TREQ_ID_200": [
            "https://github.com/dependix/platform/blob/f53f50a0ab1186329292e6b28b8e6c93b37ea41/tools/sources/bad_implementation.py#L17"
        ],
    }


def test_source_link_integration_ok(
    sphinx_app_setup,
    basic_conf,
    basic_needs,
    example_source_link_text_all_ok,
    sphinx_base_dir,
):
    app = sphinx_app_setup(basic_conf, basic_needs, example_source_link_text_all_ok)
    try:
        app.build()
        # print(f"===== EXTENSIONS: {app.extensions.keys()}")
        print(f"===== REQ-FILE: {app.env.config.requirement_links}")
        Needs_Data = SphinxNeedsData(app.env)
        needs_data = {x["id"]: x for x in Needs_Data.get_needs_view().values()}
        # print(f"========== NEEDS_DATA: {needs_data}")
        assert "TREQ_ID_1" in needs_data
        assert "TREQ_ID_2" in needs_data
        assert (
            ",".join(example_source_link_text_all_ok["TREQ_ID_1"])
            == needs_data["TREQ_ID_1"]["source_code_link"]
        )
        assert (
            ",".join(example_source_link_text_all_ok["TREQ_ID_2"])
            == needs_data["TREQ_ID_2"]["source_code_link"]
        )
    finally:
        app.cleanup()


def test_source_link_integration_non_existent_id(
    sphinx_app_setup,
    basic_conf,
    basic_needs,
    example_source_link_text_non_existent,
    sphinx_base_dir,
):
    app = sphinx_app_setup(
        basic_conf, basic_needs, example_source_link_text_non_existent
    )
    try:
        app.build()
        warnings = app._warning.getvalue()
        assert (
            "WARNING: Could not find TREQ_ID_200 in the needs id's. Found in file(s): ['tools/sources/bad_implementation.py#L17']"
            in warnings
        )
    finally:
        app.cleanup()
