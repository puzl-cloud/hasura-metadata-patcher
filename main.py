#!/usr/bin/env python3

import click
import json
from hasuraMetadata import HasuraMetadata


def read_json_file(path):
    try:
        with open(path) as input_file:
            result = json.load(input_file)
        input_file.close()

    except Exception as e:
        print("Can not read json file " + str(path) + " !")
        raise e

    return result


def convert_objects_to_hasura_metadata_schema(mixin):
    new_meta = HasuraMetadata()

    for obj in mixin.values():
        meta_object = obj["object"]
        if obj["type"] == "event_trigger":
            if "table" not in obj["object"]:
                raise Exception(f"No table specified for event_trigger {obj['object']['name']}")
            trigger_table_name = meta_object["table"]["name"]
            trigger_table_schema = meta_object["table"]["schema"]
            del meta_object["table"]
            new_meta.merge_event_trigger(trigger_table_schema, trigger_table_name, meta_object)

        if obj["type"] == "remote_schema":
            new_meta.merge_remote_schema(meta_object)

        if obj["type"] == "action":
            new_meta.merge_action(meta_object)

        if obj["type"] == "custom_type":
            new_meta.merge_custom_type(meta_object)

        if obj["type"] == "input_object":
            new_meta.merge_custom_input_type(meta_object)

    return new_meta


def patch_metadata_file(source_file, mixin_file, replace_objects=None, output_file=None, meta_version=3):
    print("Loading source file")
    source = read_json_file(source_file)
    print("Loading mixin file")
    mixin = read_json_file(mixin_file)

    print("Loading source metadata")
    try:
        source_meta = HasuraMetadata(source)
    except Exception as e:
        print("Source file is not a valid Hasura metadata file")
        raise e

    print("Loading mixin metadata")
    try:
        mixin_meta = HasuraMetadata(mixin)
    except Exception as e:
        mixin_meta = convert_objects_to_hasura_metadata_schema(mixin)

    print("Mixing metadata")
    source_meta.mixin(mixin_meta)

    if replace_objects:
        for obj in replace_objects:
            assert obj in ["event_triggers", "remote_schemas", "actions", "custom_types"], \
                'Invalid -r option. ' \
                'Must be one of ["event_triggers", "remote_schemas", "actions", "custom_types"].'

        if "event_triggers" in replace_objects:
            print("Replacing event triggers")
            source_meta.replace_event_triggers(mixin_meta.tables)
        if "remote_schemas" in replace_objects:
            print("Replacing remote schemas")
            source_meta.replace_remote_schemas(mixin_meta.remote_schemas)
        if "actions" in replace_objects:
            print("Replacing actions")
            source_meta.replace_actions(mixin_meta.actions)
        if "custom_types" in replace_objects:
            print("Replacing custom types")
            source_meta.replace_custom_types(mixin_meta.custom_types)

    try:
        if meta_version == 3:
            del source_meta.tables
        else:
            del source_meta.sources
        meta_object_for_api = source_meta.__dict__

        if output_file:
            with open(output_file, "w") as out_file:
                json.dump(meta_object_for_api, out_file, indent=2)
        else:
            with open(source_file, "w") as out_file:
                json.dump(meta_object_for_api, out_file, indent=2)
    except Exception as e:
        print("Unable to dump output")
        raise e


@click.command()
@click.option('--source', '-s', help="Path to Hasura metadata json file, which should be patched", required=True)
@click.option('--mixin', '-m', help="Path to another Hasura metadata json file or json file, "
                                    "contains metadata objects.", required=True)
@click.option('--replace', '-r', help="Pass if you want to define objects, "
                                      "which must be completely replaced at source from mixin. "
                                      "Supported object types: event_triggers, remote_schemas, actions, custom_types.",
              multiple=True, default=[])
@click.option('--output', '-o', help="Path to output json file with new metadata. "
                                     "If not set, source file will be overwritten.")
@click.option('--version', '-v', help="Version of metadata object. 2 and 3 are supported.", default=3)
def exec_command(source, mixin, replace, output, version):
    return patch_metadata_file(source, mixin, replace, output, version)


if __name__ == '__main__':
    exec_command()
