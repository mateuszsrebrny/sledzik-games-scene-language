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

    def property(self, items):
        return items[0]

    def statement(self, items):
        return items[0]

    def block(self, items):
        return self._build_object("block", items)

    def cylinder(self, items):
        return self._build_object("cylinder", items)

    def frustum(self, items):
        return self._build_object("frustum", items)

    def ring(self, items):
        return self._build_object("ring", items)

    def scene(self, items):
        return {
            "scene": items[0],
            "objects": items[1:],
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
