import json

from lark import Transformer


class SGSLTransformer(Transformer):
    def start(self, items):
        return items[0]

    def NUMBER(self, value):
        return float(value)

    def NAME(self, value):
        return str(value)

    def COLOR(self, value):
        return str(value)

    def ESCAPED_STRING(self, value):
        return json.loads(str(value))

    def number(self, items):
        return ("number", items[0])

    def variable(self, items):
        return ("variable", items[0])

    def add(self, items):
        return ("add", items[0], items[1])

    def sub(self, items):
        return ("sub", items[0], items[1])

    def mul(self, items):
        return ("mul", items[0], items[1])

    def div(self, items):
        return ("div", items[0], items[1])

    def neg(self, items):
        return ("neg", items[0])

    def at(self, items):
        return ("at", list(items))

    def size(self, items):
        return ("size", list(items))

    def radius(self, items):
        return ("radius", items[0])

    def radius_inner(self, items):
        return ("radius_inner", items[0])

    def radius_outer(self, items):
        return ("radius_outer", items[0])

    def radius_top(self, items):
        return ("radius_top", items[0])

    def radius_bottom(self, items):
        return ("radius_bottom", items[0])

    def pipe_radius(self, items):
        return ("pipe_radius", items[0])

    def bend_radius(self, items):
        return ("bend_radius", items[0])

    def angle(self, items):
        return ("angle", items[0])

    def height(self, items):
        return ("height", items[0])

    def segments(self, items):
        return ("segments", items[0])

    def anchor(self, items):
        return ("anchor", list(items))

    def rotate(self, items):
        return ("rotation", list(items))

    def color(self, items):
        return ("color", items[0])

    def transparency(self, items):
        return ("transparency", items[0])

    def param(self, items):
        return {"type": "param", "name": items[0], "value": items[1]}

    def set_param(self, items):
        return ("parameter_overrides", (items[0], items[1]))

    def import_stmt(self, items):
        return {"type": "import", "path": items[0]}

    def property(self, items):
        return items[0]

    def instance_property(self, items):
        return items[0]

    def component_statement(self, items):
        return items[0]

    def statement(self, items):
        return items[0]

    def object(self, items):
        return items[0]

    def block(self, items):
        return self._build_object("block", items)

    def cylinder(self, items):
        return self._build_object("cylinder", items)

    def frustum(self, items):
        return self._build_object("frustum", items)

    def ring(self, items):
        return self._build_object("ring", items)

    def pipe_arc(self, items):
        return self._build_object("pipe_arc", items)

    def component(self, items):
        name = items[0]
        parameters: list[dict] = []
        objects: list[dict] = []
        seen_object_names: set[str] = set()

        for item in items[1:]:
            if item["type"] == "param":
                parameters.append({"name": item["name"], "value": item["value"]})
                continue
            if item["name"] in seen_object_names:
                raise ValueError(f"Duplicate object name {item['name']!r} in component {name!r}")
            seen_object_names.add(item["name"])
            objects.append(item)

        return {
            "type": "component_definition",
            "name": name,
            "parameters": parameters,
            "objects": objects,
        }

    def instance(self, items):
        name = items[0]
        component_name = items[1]
        data = {
            "type": "component_instance",
            "name": name,
            "component": component_name,
            "parameter_overrides": {},
        }
        for key, value in items[2:]:
            if key == "parameter_overrides":
                param_name, param_value = value
                if param_name in data["parameter_overrides"]:
                    raise ValueError(f"Duplicate parameter override {param_name!r} in instance {name!r}")
                data["parameter_overrides"][param_name] = param_value
                continue
            if key in data:
                raise ValueError(f"Duplicate property {key!r} in component instance {name!r}")
            data[key] = value
        return data

    def scene(self, items):
        return {
            "scene": items[0],
            "statements": items[1:],
        }

    def _build_object(self, object_type, items):
        name = items[0]
        data = {
            "type": object_type,
            "name": name,
        }
        for key, value in items[1:]:
            if key in data:
                raise ValueError(f"Duplicate property {key!r} in {object_type} {name!r}")
            data[key] = value
        return data
