import importlib.util


def format_kwargs(**kwargs):
    "jaiminho_django_project.send decoder=InternalDecoder|jaiminho_django_project.foo foo=Bar;int x=2"
    arguments = []
    for name, value in kwargs.items():
        if isinstance(value, (int, str, float)):
            arguments.append(f"{value.__class__.__name__} {name}={value}")
        elif isinstance(value, type):
            arguments.append(f"{value.__module__}.{value.__name__} {name}=NotUsed")
        else:
            raise NotImplementedError("Unsupported argument type")

    return "|".join(arguments)


def load_argument(argument):
    equal_pos = argument.find("=")
    value = argument[equal_pos + 1 :]
    name = argument[:equal_pos]
    class_path, key = name.split(" ")
    if class_path in ("int", "float", "str"):
        return key, eval(class_path)(value)
    else:
        module_path = ".".join(class_path.split(".")[:-1])
        class_name = class_path.split(".")[-1]
        module_spec = importlib.util.find_spec(module_path)
        module = module_spec.loader.load_module()
        return key, getattr(module, class_name)


def load_kwargs(kwargs_string):
    if not kwargs_string:
        return {}

    arguments = [load_argument(argument) for argument in kwargs_string.split("|")]
    return {key: value for key, value in arguments}
