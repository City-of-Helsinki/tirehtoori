import json
from pathlib import Path

import pytest

import conf_parser.parse_domain_files as parser
from conf_parser.parse_domain_files import (
    ConfigProcessor,
    ParseError,
    find_server_blocks,
)


def make_location(args, block=None, line=None):
    location = {
        "directive": "location",
        "args": args,
        "block": [] if block is None else block,
    }
    if line is not None:
        location["line"] = line
    return location


def make_return(args):
    return {"directive": "return", "args": args}


def make_rewrite(args):
    return {"directive": "rewrite", "args": args}


@pytest.mark.parametrize(
    ("uri", "expected"),
    [
        (
            "/foo",
            {
                "uri": "/foo",
                "append_subpath": False,
                "match_subpaths": False,
                "pass_query_string": False,
            },
        ),
        (
            "^/foo$",
            {
                "uri": "/foo",
                "append_subpath": False,
                "match_subpaths": False,
                "pass_query_string": False,
            },
        ),
        (
            "/foo(.*)",
            {
                "uri": "/foo",
                "append_subpath": False,
                "match_subpaths": True,
                "pass_query_string": False,
            },
        ),
        (
            "/foo/$1",
            {
                "uri": "/foo/",
                "append_subpath": True,
                "match_subpaths": False,
                "pass_query_string": False,
            },
        ),
        (
            "/foo/$1$is_args$args",
            {
                "uri": "/foo/",
                "append_subpath": True,
                "match_subpaths": False,
                "pass_query_string": True,
            },
        ),
        (
            "/foo/$args",
            {
                "uri": "/foo/",
                "append_subpath": False,
                "match_subpaths": False,
                "pass_query_string": True,
            },
        ),
        (
            "/foo/$is_args$args",
            {
                "uri": "/foo/",
                "append_subpath": False,
                "match_subpaths": False,
                "pass_query_string": True,
            },
        ),
        (
            "https://bar.test/path?source=nginx",
            {
                "uri": "https://bar.test/path?source=nginx",
                "append_subpath": False,
                "match_subpaths": False,
                "pass_query_string": False,
            },
        ),
    ],
)
def test_parse_uri_supports_documented_patterns(uri, expected):
    processor = ConfigProcessor()

    assert processor._parse_uri(uri) == expected


@pytest.mark.parametrize(
    "uri",
    [
        "/foo$",
        "https://$host/foo",
        "/foo/(.*)/bar",
        "/foo/$1/bar",
    ],
)
def test_parse_uri_rejects_unsupported_patterns(uri):
    processor = ConfigProcessor()

    with pytest.raises(ParseError):
        processor._parse_uri(uri)


def test_get_block_from_server_conf_handles_single_line_and_blocks(tmp_path):
    conf_file = tmp_path / "server.conf"
    conf_file.write_text(
        "server {\n"
        "    location /foo {\n"
        "        return 301 https://bar.test;\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    processor = ConfigProcessor(filename="server.conf", conf_file_path=str(conf_file))

    assert processor._get_block_from_server_conf({"line": 1}) == {
        "start": 0,
        "end": 0,
        "lines": "server {",
    }
    assert processor._get_block_from_server_conf({"line": 2, "block": []}) == {
        "start": 2,
        "end": 4,
        "lines": [
            "    location /foo {",
            "        return 301 https://bar.test;",
            "    }",
        ],
    }
    assert processor._get_block_from_server_conf({"directive": "listen"}) is None


def test_get_block_from_server_conf_rejects_unclosed_block():
    processor = ConfigProcessor()
    processor.server_conf = ["location /foo {"]

    with pytest.raises(ParseError, match="Block not closed"):
        processor._get_block_from_server_conf({"line": 1, "block": []})


def test_process_server_name_and_ignore_unknown_directives():
    processor = ConfigProcessor()

    processor.process_directive(
        {"directive": "server_name", "args": ["example.test", "www.example.test"]}
    )
    processor.process_directive({"directive": "listen", "args": ["8080"]})

    assert processor.domain_names == ["example.test", "www.example.test"]
    assert processor.rules == []
    assert processor.warnings == []


@pytest.mark.parametrize(
    ("args", "case_sensitive"),
    [
        (["/foo"], True),
        (["=", "/foo"], True),
        (["~", "/foo"], True),
        (["~*", "/foo"], False),
        (["^~", "/foo"], False),
    ],
)
def test_process_location_sets_case_sensitivity(args, case_sensitive):
    processor = ConfigProcessor()

    processor.process_directive(make_location(args))

    assert processor.rules == []
    assert processor.warnings == []


def test_process_location_and_return_include_source_notes(tmp_path):
    conf_file = tmp_path / "server.conf"
    conf_file.write_text(
        "server {\n"
        "    location ~* /from {\n"
        "        return 301 https://bar.test;\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    processor = ConfigProcessor(filename="server.conf", conf_file_path=str(conf_file))
    location = make_location(
        ["~*", "/from"], [make_return(["301", "https://bar.test"])], line=2
    )

    processor.process_directive(location)

    assert processor.rules[0] == {
        "case_sensitive": False,
        "path": "/from",
        "permanent": True,
        "destination": "https://bar.test/",
        "match_subpaths": False,
        "append_subpath": False,
        "pass_query_string": False,
        "notes": (
            "Parsed automatically from server.conf\n"
            "Block from line 2 to 4:\n"
            "    location ~* /from {\n"
            "        return 301 https://bar.test;\n"
            "    }"
        ),
        "raw_destination": "https://bar.test",
        "raw_path": "/from",
        "source_directive": "return",
    }


@pytest.mark.parametrize(
    ("response_code", "permanent"), [("301", True), ("302", False)]
)
def test_process_return_supports_redirect_status_codes(response_code, permanent):
    processor = ConfigProcessor()
    location = make_location(
        ["~*", "/from"], [make_return([response_code, "https://bar.test"])]
    )

    processor.process_directive(location)

    assert processor.rules[0]["permanent"] is permanent
    assert processor.rules[0]["destination"] == "https://bar.test/"


def test_process_return_handles_subpath_and_query_suffixes():
    processor = ConfigProcessor()
    location = make_location(
        ["~*", "/from(.*)"],
        [make_return(["302", "https://bar.test/$1$is_args$args"])],
    )

    processor.process_directive(location)

    assert processor.rules[0]["path"] == "/from"
    assert processor.rules[0]["destination"] == "https://bar.test/"
    assert processor.rules[0]["match_subpaths"] is True
    assert processor.rules[0]["append_subpath"] is True
    assert processor.rules[0]["pass_query_string"] is True


@pytest.mark.parametrize(
    ("return_args", "warning"),
    [
        (["404"], "Invalid number of arguments in return directive"),
        (
            ["307", "https://bar.test"],
            "Invalid response code 307 in return directive",
        ),
    ],
)
def test_process_return_warns_for_unsupported_directives(return_args, warning):
    processor = ConfigProcessor()
    processor.process_directive(make_location(["/from"], [make_return(return_args)]))

    assert processor.rules == []
    assert processor.warnings[0]["message"] == warning


def test_process_return_warns_for_destination_wildcards():
    processor = ConfigProcessor()
    processor.process_directive(
        make_location(["/from"], [make_return(["301", "https://bar.test/(.*)"])])
    )

    assert processor.rules == []
    assert processor.warnings[0]["message"] == "(.*) not allowed in destination URI"


def test_process_location_skips_multiple_directives():
    processor = ConfigProcessor()
    location = make_location(
        ["/from"], [make_return(["301", "https://bar.test"]), make_return(["302"])]
    )

    processor.process_directive(location)

    assert processor.rules == []
    assert processor.warnings[0]["message"] == (
        "More than one directive in location block, skipping"
    )


def test_process_rewrite_supports_implicit_permanent_redirect():
    processor = ConfigProcessor()
    location = make_location(
        ["=", "/from"],
        [make_rewrite(["/from(.*)", "https://bar.test/$1$is_args$args"])],
    )

    processor.process_directive(location)

    assert processor.rules[0] == {
        "case_sensitive": True,
        "path": "/from",
        "permanent": True,
        "destination": "https://bar.test/",
        "match_subpaths": True,
        "append_subpath": True,
        "pass_query_string": True,
        "notes": "",
        "raw_destination": "https://bar.test/$1$is_args$args",
        "raw_path": "/from(.*)",
        "source_directive": "rewrite",
    }


def test_process_rewrite_disables_query_passing_when_replacement_ends_with_question_mark():
    processor = ConfigProcessor()
    location = make_location(
        ["/from"], [make_rewrite(["/from(.*)", "/to?", "redirect"])]
    )

    processor.process_directive(location)

    assert processor.rules[0]["permanent"] is False
    assert processor.rules[0]["destination"] == "/to"
    assert processor.rules[0]["pass_query_string"] is False


@pytest.mark.parametrize(
    ("rewrite_args", "warning"),
    [
        (
            ["/other", "/to", "redirect"],
            "Rewrite directive regex does not match parent location",
        ),
        (["/from", "/to", "foo"], "Invalid flag foo in rewrite directive"),
    ],
)
def test_process_rewrite_warns_for_unsupported_directives(rewrite_args, warning):
    processor = ConfigProcessor()
    processor.process_directive(make_location(["/from"], [make_rewrite(rewrite_args)]))

    assert processor.rules == []
    assert processor.warnings[0]["message"] == warning


def test_server_level_redirect_directives_are_warned():
    processor = ConfigProcessor()

    processor.process_directive(make_return(["301", "https://bar.test"]))
    processor.process_directive(make_rewrite(["/from", "/to", "redirect"]))

    assert [warning["message"] for warning in processor.warnings] == [
        "Return directive found in server block",
        "Rewrite directive found in server block",
    ]


def test_rewrite_outside_location_block_is_warned():
    processor = ConfigProcessor()

    processor.process_directive(
        make_rewrite(["/from", "/to", "redirect"]),
        parent={"path": "/from"},
        parent_raw={"directive": "server", "args": ["server"]},
    )

    assert processor.rules == []
    assert processor.warnings[0]["message"] == (
        "Rewrite directive found outside location block"
    )


def test_debug_data_can_be_disabled(monkeypatch):
    monkeypatch.setattr(parser, "INCLUDE_DEBUG_DATA", False)
    processor = ConfigProcessor()

    processor.process_directive(
        make_location(["/from"], [make_return(["301", "https://bar.test"])])
    )

    assert "raw_destination" not in processor.rules[0]
    assert "raw_path" not in processor.rules[0]
    assert "source_directive" not in processor.rules[0]


def test_find_server_blocks_returns_only_server_directives():
    server_block = {"directive": "server", "block": []}
    map_block = {"directive": "map", "block": []}
    config = {"config": [{"parsed": [{"block": [server_block, map_block]}]}]}

    assert find_server_blocks(config) == [server_block]


def test_process_sample_configuration(tmp_path, monkeypatch):
    monkeypatch.setattr(parser, "TEMP_CONF_DIR", str(tmp_path / "conf"))
    monkeypatch.setattr(parser, "CROSSPLANE_JSON_DIR", str(tmp_path / "json"))
    monkeypatch.setattr(parser, "GENERATE_CROSSPLANE_JSON", True)
    parser.build_directories()

    sample_file = Path(__file__).parents[1] / "sample_conf.yml"
    output = parser.process(str(sample_file))

    assert [item["domain_names"] for item in output] == [
        ["www.foo.test", "foo.test"],
        ["redirect-to-foo.test"],
    ]
    assert [len(item["rules"]) for item in output] == [7, 0]
    assert [len(item["warnings"]) for item in output] == [2, 1]
    assert output[0]["rules"][0]["destination"] == "https://google.com/"
    assert output[0]["rules"][0]["append_subpath"] is True
    assert output[1]["warnings"][0]["message"] == (
        "Return directive found in server block"
    )
    assert (tmp_path / "json" / "sample_conf_server.conf.json").is_file()


def test_main_writes_aggregated_results(tmp_path, monkeypatch):
    domains_dir = tmp_path / "domains"
    domains_dir.mkdir()
    sample_file = Path(__file__).parents[1] / "sample_conf.yml"
    (domains_dir / sample_file.name).write_text(
        sample_file.read_text(encoding="utf-8"), encoding="utf-8"
    )
    results_file = tmp_path / "results.json"
    monkeypatch.setattr(parser, "DOMAINS_DIR", str(domains_dir))
    monkeypatch.setattr(parser, "TEMP_CONF_DIR", str(tmp_path / "conf"))
    monkeypatch.setattr(parser, "CROSSPLANE_JSON_DIR", str(tmp_path / "json"))
    monkeypatch.setattr(parser, "RESULTS_FILE", str(results_file))
    monkeypatch.setattr(parser, "GENERATE_CROSSPLANE_JSON", False)
    monkeypatch.setattr(parser, "DELETE_TEMP_FILES", False)

    parser.main()

    result = json.loads(results_file.read_text(encoding="utf-8"))
    assert [item["domain_names"] for item in result["results"]] == [
        ["www.foo.test", "foo.test"],
        ["redirect-to-foo.test"],
    ]
    assert [len(item["rules"]) for item in result["results"]] == [7, 0]
    assert len(result["warnings"]) == 3


def test_cleanup_removes_temporary_directories(tmp_path, monkeypatch):
    conf_dir = tmp_path / "conf"
    json_dir = tmp_path / "json"
    conf_dir.mkdir()
    json_dir.mkdir()
    (conf_dir / "server.conf").write_text("server {}", encoding="utf-8")
    (json_dir / "server.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(parser, "TEMP_CONF_DIR", str(conf_dir))
    monkeypatch.setattr(parser, "CROSSPLANE_JSON_DIR", str(json_dir))
    monkeypatch.setattr(parser, "DELETE_TEMP_FILES", True)

    parser.cleanup()

    assert not conf_dir.exists()
    assert not json_dir.exists()
