class HasuraMetadata:
    def __init__(self, source=None):
        if not source:
            self.version = 3
            self.tables = list()
            self.sources = list()
            self.remote_schemas = list()
            self.actions = list()
            self.custom_types = dict()
            self.custom_types["objects"] = list()
            self.custom_types["input_objects"] = list()

        else:
            supported_versions = [2, 3]
            if source["version"] not in supported_versions:
                raise Exception(f"Unsupported Hasura metadata version: versions {supported_versions} are supported, "
                                f"got {source['version']} instead")

            self.version = source["version"]

            #
            # ToDo: add many sources support
            if self.version == 3:
                self.sources = source["sources"]
                self.tables = source["sources"][0]["tables"]
            else:
                self.tables = source["tables"]

            if "remote_schemas" in source:
                self.remote_schemas = source["remote_schemas"]
            else:
                self.remote_schemas = list()

            if "actions" in source:
                self.actions = source["actions"]
            else:
                self.actions = list()

            if "custom_types" in source:
                self.custom_types = source["custom_types"]
            else:
                self.custom_types = dict()
            if 'objects' not in self.custom_types:
                self.custom_types["objects"] = list()
            if 'input_objects' not in self.custom_types:
                self.custom_types["input_objects"] = list()

    def _apply_table(self, schema, name):
        table = self.__get_table(schema, name)
        if not table:
            self.tables.append({"table": {
                "name": name,
                "schema": schema
            }})
            table = self.__get_table(schema, name)

        if "event_triggers" not in table:
            table["event_triggers"] = list()

        return table

    def __get_table(self, schema, name):
        for table in self.tables:
            if table["table"]["name"] == name and table["table"]["schema"] == schema:
                return table
        return None

    def __get_event_trigger(self, schema, table_name, event_trigger_name):
        table = self.__get_table(schema, table_name)
        if table and "event_triggers" in table:
            for trigger in table["event_triggers"]:
                if trigger["name"] == event_trigger_name:
                    return trigger

        return None

    def merge_event_trigger(self, schema, table_name, event_trigger):
        assert "name" in event_trigger, "Event trigger must have name"
        assert type(event_trigger) is dict, "Event trigger must be object"

        table = self._apply_table(schema, table_name)
        existed_trigger = self.__get_event_trigger(schema, table_name, event_trigger["name"])
        if existed_trigger:
            table["event_triggers"].remove(existed_trigger)

        table["event_triggers"].append(event_trigger)
        return self

    def merge_remote_schema(self, remote_schema):
        assert "name" in remote_schema, "Remote schema must have name"
        assert type(remote_schema) is dict, "Remote schema must be object"

        for sch in self.remote_schemas.copy():
            if sch["name"] == remote_schema["name"]:
                self.remote_schemas.remove(sch)
                break

        self.remote_schemas.append(remote_schema)
        return self

    def merge_action(self, action):
        assert "name" in action, "Action must have name"
        assert type(action) is dict, "Action must be object"

        for act in self.actions.copy():
            if act["name"] == action["name"]:
                self.actions.remove(act)
                break

        self.actions.append(action)
        return self

    def merge_custom_type(self, custom_type):
        assert "name" in custom_type, "Custom type must have name"
        assert type(custom_type) is dict, "Custom type must be object"

        for c_type in self.custom_types["objects"].copy():
            if c_type["name"] == custom_type["name"]:
                self.custom_types["objects"].remove(c_type)
                break

        self.custom_types["objects"].append(custom_type)
        return self

    def merge_custom_input_type(self, custom_input_type):
        assert "name" in custom_input_type, "Custom input type object must have name"
        assert type(custom_input_type) is dict, "Custom input type must be object"

        for i_object in self.custom_types["input_objects"].copy():
            if i_object["name"] == custom_input_type["name"]:
                self.custom_types["input_objects"].remove(i_object)
                break

        self.custom_types["input_objects"].append(custom_input_type)
        return self

    def replace_remote_schemas(self, new_remote_schemas):
        assert type(new_remote_schemas) is list, "New remote schemas must be list"
        self.remote_schemas = new_remote_schemas
        return self

    def replace_actions(self, new_actions):
        assert type(new_actions) is list, "New actions must be list"
        self.actions = new_actions
        return self

    def replace_custom_types(self, new_custom_types):
        assert type(new_custom_types) is dict, "New custom types must be dict"
        self.custom_types = new_custom_types
        return self

    def replace_event_triggers(self, new_tables):
        assert type(new_tables) is list, "New tables must be list"
        for new_table in new_tables:
            existed_table = self._apply_table(new_table["table"]["schema"], new_table["table"]["name"])
            if "event_triggers" in new_table:
                existed_table["event_triggers"] = new_table["event_triggers"]
            else:
                del existed_table["event_triggers"]
        #
        # If there is no table in new tables list, then there is no event triggers
        # -> all existed event triggers in this table should be removed (i.e. replaced to nothing)
        for table in self.tables:
            new_table_found = False
            for new_table in new_tables:

                #
                # Do nothing, if we found a table
                if new_table["table"]["name"] == table["table"]["name"] \
                        and new_table["table"]["schema"] == table["table"]["schema"]:
                    new_table_found = True
                    break

            if not new_table_found and "event_triggers" in table:
                del table["event_triggers"]

        return self

    def mixin(self, mixin_hasura_metadata):
        assert type(mixin_hasura_metadata) is HasuraMetadata, "mixin_hasura_metadata must be instance of HasuraMetadata"
        for table in mixin_hasura_metadata.tables:
            if "event_triggers" in table:
                for event_trigger in table["event_triggers"]:
                    self.merge_event_trigger(table["table"]["schema"], table["table"]["name"], event_trigger)

        for remote_schema in mixin_hasura_metadata.remote_schemas:
            self.merge_remote_schema(remote_schema)

        for action in mixin_hasura_metadata.actions:
            self.merge_action(action)

        for custom_type in mixin_hasura_metadata.custom_types["objects"]:
            self.merge_custom_type(custom_type)

        for input_object in mixin_hasura_metadata.custom_types["input_objects"]:
            self.merge_custom_type(input_object)
