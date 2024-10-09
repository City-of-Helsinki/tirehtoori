import json
import os
import re
from urllib.parse import urlsplit

import crossplane
import yaml

# Generate crossplane JSON files for easier debugging
GENERATE_CROSSPLANE_JSON = True
CROSSPLANE_JSON_DIR = "./.temp/json"

# Delete temporary files after processing
DELETE_TEMP_FILES = False

# Include debug data in the results
INCLUDE_DEBUG_DATA = True

# Directory for domain yaml files
DOMAINS_DIR = "./.temp/domains"
# Temporary directory for crossplane to parse the files
TEMP_CONF_DIR = "./.temp/conf"
# File to write the results to
RESULTS_FILE = "./.temp/results.json"


class ParseError(Exception):
    pass


class ConfigProcessor:
    # Map directives to methods that process them
    _DIRECTIVE_PROCESSORS = {
        "server_name": "_process_server_name",
        "location": "_process_location",
        "rewrite": "_process_rewrite",
        "return": "_process_return",
    }

    def __init__(self, filename=None):
        self.rules = []
        self.domain_names = None
        self.warnings = []
        # File name is for informative purposes only
        self.filename = filename

    def _parse_uri(self, uri: str):
        if not uri.startswith("^") and uri.endswith("$"):
            # E.g. /foo/$. Shouldn't have any cases like these, but just in case...
            raise ParseError("$ anchor only not supported")

        stripped_uri = uri.strip("^$")
        split_uri = urlsplit(stripped_uri)

        if split_uri.netloc == "$host":
            raise ParseError("$host not allowed in URI")

        # The query part might not actually be a query, but some regex like (.*)?$
        path_with_query = f"{split_uri.path}?{split_uri.query}"
        # For our purposes, these are essentially the same, but the latter is easier
        # to parse.
        path_with_query = path_with_query.replace("(/.*)", "/(.*)")
        segments = path_with_query.split("/")

        append_subpath = False
        match_subpaths = False
        pass_query_string = False

        # Process each segment. Find any unallowed terms, and set flags if needed.
        for i, segment in enumerate(segments):
            # Not the last segment
            if i < len(segments) - 1:
                unallowed_terms = [r"\(\.\*\)", r"\$\d+"]
                if any(re.match(term, segment) for term in unallowed_terms):
                    raise ParseError(f"Unallowed term in segment {segment}, path {uri}")
            # Last segment
            else:
                # Remove any trailing ? that might've been added before segment
                # processing.
                segment = segment.removesuffix("?")

                # Check for any usual suspects
                if segment.endswith("$1$is_args$args"):
                    append_subpath = True
                    pass_query_string = True
                    segment = segment.removesuffix("$1$is_args$args")
                elif segment.endswith("$1"):
                    append_subpath = True
                    segment = segment.removesuffix("$1")
                elif segment.endswith("(.*)"):
                    match_subpaths = True
                    segment = segment.removesuffix("(.*)")
                elif segment.endswith("$args"):
                    pass_query_string = True
                    segment = segment.removesuffix("$args")
                elif segment.endswith("$is_args$args"):
                    pass_query_string = True
                    segment = segment.removesuffix("$is_args$args")

                suffix_only_terms = [
                    r"\(\.\*\)",
                    r"\$args",
                    r"\$is_args\$args" r"\$\d+",
                ]
                # Any allowed suffixes should be removed by now, so if any of these
                # are found, it's an error.
                if any(re.match(term, segment) for term in suffix_only_terms):
                    raise ParseError(
                        f"Unallowed term in last segment {segment}, path {uri}"
                    )
            segments[i] = segment

        # Rejoin the split URI with the parsed segments
        joined_segments = "/".join(segments).removesuffix("?")
        if not joined_segments.startswith("/"):
            joined_segments = f"/{joined_segments}"
        host_with_scheme = (
            f"{split_uri.scheme}://{split_uri.netloc}" if split_uri.netloc else ""
        )

        return {
            "uri": f"{host_with_scheme}{joined_segments}",
            "append_subpath": append_subpath,
            "match_subpaths": match_subpaths,
            "pass_query_string": pass_query_string,
        }

    def _process_server_name(self, directive, *_):
        self.domain_names = directive["args"]

    def _process_location(self, directive, *_):
        if len(directive["block"]) > 1:
            self.add_warning(
                "More than one directive in location block, skipping",
                directive,
            )
            return

        case_sensitive_arg = directive["args"][0]
        if case_sensitive_arg in ["=", "~", "~*", "^~"]:
            case_sensitive = case_sensitive_arg in ["=", "~"]
            path = directive["args"][1]
        else:
            case_sensitive = True
            # Case sensitivity can be omitted, in which case the first argument is
            # the path
            path = directive["args"][0]

        parsed_uri = self._parse_uri(path)
        parsed = {
            "case_sensitive": case_sensitive,
            "path": parsed_uri["uri"],
            "raw_path": path,
            "match_subpaths": parsed_uri["match_subpaths"],
        }

        for location_directive in directive["block"]:
            self.process_directive(
                location_directive, parent=parsed, parent_raw=directive
            )

    def _process_rewrite(self, directive, parent, parent_raw):
        if parent is None:
            self.add_warning(
                "Rewrite directive found in server block",
                directive,
            )
            return

        assert parent_raw["directive"] == "location"

        case_sensitive_arg = parent_raw["args"][0]
        if case_sensitive_arg in ["=", "^~"]:
            self.add_warning(
                f"Location directive {case_sensitive_arg} found",
                directive,
            )

        try:
            regex, replacement, flag = directive["args"]
        except ValueError:
            regex, replacement = directive["args"]
            flag = "permanent" if replacement.startswith("http") else "redirect"

        regex = regex.strip("^$")
        # To keep it simple as possible, we only support regexes that match the
        # parent location. E.g.
        # location /foo {
        #     rewrite ^/foo/(.*) /bar/$1;
        # }
        # is fine, but
        # location /foo {
        #     rewrite (.*) /bar/$1;
        # }
        # is not. Even though they're essentially the same, the latter is more
        # error-prone for parsing.
        if not regex.startswith(parent["path"]):
            self.add_warning(
                "Rewrite directive regex does not match parent location",
                directive,
            )
            return
        assert flag in ["redirect", "permanent"]

        parsed_regex = self._parse_uri(regex)
        parsed_replacement = self._parse_uri(replacement)

        rule = {
            "case_sensitive": parent["case_sensitive"],
            "path": parsed_regex["uri"],
            "permanent": flag == "permanent",
            "destination": parsed_replacement["uri"],
            "match_subpaths": parsed_regex["match_subpaths"],
            "append_subpath": parsed_replacement["append_subpath"],
            # nginx rewrites pass the query string by default, unless there's
            # a query string in the replacement
            "pass_query_string": parsed_replacement["pass_query_string"]
            or not replacement.endswith("?"),
        }
        if INCLUDE_DEBUG_DATA:
            rule = {
                **rule,
                "raw_destination": replacement,
                "raw_path": regex,
                "source_directive": "rewrite",
            }
        self.rules.append(rule)

    def _process_return(self, directive, parent, parent_raw):
        if parent is None:
            self.add_warning(
                "Return directive found in server block",
                directive,
            )
            return

        # Not sure if there's a return for any other directive than location,
        # and not about to find out, either.
        assert parent_raw["directive"] == "location"

        case_sensitive_arg = parent_raw["args"][0]
        if case_sensitive_arg in ["=", "^~"]:
            self.add_warning(
                f"Location directive {case_sensitive_arg} found",
                directive,
            )

        try:
            # E.g. "return 301 https://foo.test;"
            response_code, destination = directive["args"]
        except ValueError:
            # E.g. "return 404;"
            self.add_warning(
                "Invalid number of arguments in return directive",
                directive,
            )
            return

        if response_code not in ["301", "302"]:
            # Support redirect and permanent redirect only
            self.add_warning(
                f"Invalid response code {response_code} in return directive",
                directive,
            )
            return

        parsed_uri = self._parse_uri(destination)

        # Sanity check, something is probably wrong if return ends with (.*)
        assert parsed_uri["match_subpaths"] is False

        rule = {
            "case_sensitive": parent["case_sensitive"],
            "path": parent["path"],
            "permanent": response_code == "301",
            "destination": parsed_uri["uri"],
            "match_subpaths": parent["match_subpaths"],
            "append_subpath": parsed_uri["append_subpath"],
            "pass_query_string": parsed_uri["pass_query_string"],
        }
        if INCLUDE_DEBUG_DATA:
            rule = {
                **rule,
                "raw_destination": destination,
                "raw_path": parent["raw_path"],
                "source_directive": "return",
            }
        self.rules.append(rule)

    def process_directive(self, directive, parent=None, parent_raw=None):
        """
        Process a single directive.
        :param directive: The directive to process
        :param parent: The parsed parent directive, if any
        :param parent_raw: The raw parent directive, if any
        """

        directive_type = directive["directive"]
        if directive_type in self._DIRECTIVE_PROCESSORS:
            try:
                getattr(self, self._DIRECTIVE_PROCESSORS[directive_type])(
                    directive, parent, parent_raw
                )
            except ParseError as e:
                self.add_warning(str(e), directive)

    def add_warning(self, message, directive):
        # Warn for any anomalies
        self.warnings.append(
            {
                "message": message,
                "domain": self.domain_names,
                "filename": self.filename,
                "directive": directive,
            }
        )

    def to_json(self):
        return {
            "domain_names": self.domain_names,
            "rules": self.rules,
            "warnings": self.warnings,
        }


def find_server_blocks(server_conf):
    blocks = []
    for block in server_conf["config"][0]["parsed"][0]["block"]:
        if block["directive"] == "server":
            blocks.append(block)
    return blocks


def process(file_path):
    filename = f'{"_".join(os.path.basename(file_path).split(".")[:-1])}_server.conf'

    with open(file_path, "r") as f:
        server_conf_from_yaml = yaml.load(f, yaml.Loader)["data"]["server.conf"]
    server_conf_from_yaml = server_conf_from_yaml.replace("${DOLLAR}", "$")

    # crossplane parses only files, so we need to write the content to a file.
    with open(f"{TEMP_CONF_DIR}/{filename}", "w") as f:
        # Add a dummy http block to make crossplane happy
        f.write(f"http {{{server_conf_from_yaml}}}")

    # Parse the file we just wrote with crossplane
    server_conf = crossplane.parse(f"{TEMP_CONF_DIR}/{filename}")

    if GENERATE_CROSSPLANE_JSON:
        # Also write the parsed content to a JSON file, for easier debugging
        with open(f"{CROSSPLANE_JSON_DIR}/{filename}.json", "w") as f:
            json.dump(server_conf, f, indent=4)

    server_blocks = find_server_blocks(server_conf)

    output = []
    for server_block in server_blocks:
        # Sanity check
        assert server_block["directive"] == "server"
        config_processor = ConfigProcessor(filename=filename)
        for directive in server_block["block"]:
            config_processor.process_directive(directive)
        output.append(config_processor.to_json())

    return output


def build_directories():
    for directory in [
        TEMP_CONF_DIR,
        CROSSPLANE_JSON_DIR if GENERATE_CROSSPLANE_JSON else None,
    ]:
        if directory is None:
            continue
        if not os.path.exists(directory):
            os.makedirs(directory)


def cleanup():
    if DELETE_TEMP_FILES:
        for directory in [TEMP_CONF_DIR, CROSSPLANE_JSON_DIR]:
            if os.path.exists(directory):
                if os.path.isdir(directory):
                    for f in os.listdir(directory):
                        os.remove(f"{directory}/{f}")
                    os.rmdir(directory)
                else:
                    os.remove(directory)


def main():
    # Check that the domains dir exists
    if not os.path.exists(DOMAINS_DIR):
        raise FileNotFoundError(f"Directory {DOMAINS_DIR} not found")

    build_directories()

    results = []
    warnings = []
    # Process each file in the domains directory
    for filename in os.listdir(DOMAINS_DIR):
        process_results = process(f"{DOMAINS_DIR}/{filename}")
        results.extend(
            [
                {
                    "domain_names": item["domain_names"],
                    "rules": item["rules"],
                }
                for item in process_results
            ]
        )
        for item in process_results:
            warnings.extend(item["warnings"])

    # Write the results to a file
    with open(RESULTS_FILE, "w") as f:
        json.dump(
            {
                "results": results,
                "warnings": warnings,
            },
            f,
            indent=4,
        )

    cleanup()


if __name__ == "__main__":
    main()
