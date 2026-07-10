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

    def anchor(self, items):
        return ("anchor", list(items))

    def color(self, items):
        return ("color", items[0])

    def transparency(self, items):
        return ("transparency", items[0])

    def property(self, items):
        return items[0]

    def statement(self, items):
        return items[0]

    def block(self, items):
        name = items[0]
        data = {
            "type": "block",
            "name": name,
        }
        for key, value in items[1:]:
            if key in data:
                raise ValueError(f"Duplicate property {key!r} in block {name!r}")
            data[key] = value
        return data

    def scene(self, items):
        return {
            "scene": items[0],
            "objects": items[1:],
        }
