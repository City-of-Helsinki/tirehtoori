A one-off parser for parsing nginx redirect rules from Azure configuration files and converting them to
Tirehtööri-friendly JSON format.

## Usage
1. Install dependencies: `pip install -r requirements.txt`
2. Copy the YAML files to parse under the directory pointed  in `DOMAINS_DIR` (default: `./.temp/domains`)
3. Change any other settings in `parse_domain_files.py` if needed
4. Run the script: `python parse_domain_files.py`
5. The output will be saved to `./.temp/results.json` by default

A sample file is provided (`sample_conf.yml`).

## Restrictions
Only parses the redirect rule if the following conditions are met:
- Must be in a `location` block
- Must have only a single `return` or `rewrite` directive
- Status code must resolve to either 301 or 302
- No regex or variables used in any path segments preceding the last one
- A $ anchor must be matched with a ^ anchor
- Limited set of regex/variables allowed in the last path segment (these must be the very last part of the segment!):
  - `(.*)`
  - `$1`
  - `$1$is_args$args`
  - `$args`
  - `$is_args$args`

### Settings

- `DOMAINS_DIR`: Directory containing the YAML files to parse (default: `./.temp/domains`).
- `RESULTS_FILE`: Path to the output JSON file (default: `./.temp/results.json`).
- `TEMP_CONF_DIR`: Temporary directory for storing intermediate configuration files.
  - Due to how crossplane works, the configuration files must be stored in a directory.
- `CROSSPLANE_JSON_DIR`: Directory for storing crossplane JSON files if `GENERATE_CROSSPLANE_JSON` is enabled.
- `INCLUDE_DEBUG_DATA`: Boolean flag to include debug data in the output.
- `GENERATE_CROSSPLANE_JSON`: Boolean flag to generate crossplane JSON files for debugging.
- `DELETE_TEMP_FILES`: Boolean flag to delete temporary files after processing.

## Output format

Schema:
```json
{
  "type": "object",
  "properties": {
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "domain_names": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "rules": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "case_sensitive": {
                  "type": "boolean"
                },
                "path": {
                  "type": "string"
                },
                "permanent": {
                  "type": "boolean"
                },
                "destination": {
                  "type": "string"
                },
                "match_subpaths": {
                  "type": "boolean"
                },
                "append_subpath": {
                  "type": "boolean"
                },
                "pass_query_string": {
                  "type": "boolean"
                },
                "raw_destination": {
                  "type": "string",
                  "description": "Debug only"
                },
                "raw_path": {
                  "type": "string",
                  "description": "Debug only"
                },
                "source_directive": {
                  "type": "string",
                  "description": "Debug only"
                }
              },
              "required": [
                "case_sensitive",
                "path",
                "permanent",
                "destination",
                "match_subpaths",
                "append_subpath",
                "pass_query_string"
              ]
            }
          }
        },
        "required": ["domain_names", "rules"]
      }
    },
    "warnings": {
      "type": "array",
      "items": {
        "type": "object"
      }
    }
  },
  "required": ["results", "warnings"]
}
```

Sample output:
```json
{
  "results": [
    {
      "domain_names": ["example.com"],
      "rules": [
        {
          "case_sensitive": false,
          "path": "/foo",
          "permanent": true,
          "destination": "https://bar.test",
          "match_subpaths": true,
          "append_subpath": true,
          "pass_query_string": false,
          "raw_destination": "https://bar.test/$1",
          "raw_path": "/(.*)",
          "source_directive": "return"
        }
      ]
    }
  ],
  "warnings": [
    {
      "message": "Skipped something that's not supported"
    }
  ]
}
```
