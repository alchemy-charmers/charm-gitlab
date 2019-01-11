# Overview
<a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="Apache 2.0 License"></a>

This base layer provides a function to read options defined in `layer.yaml` file.
The options can be specified in multiple sections, generally one per layer included
in the final built charm.  Each layer can define what options it can accept in the
same format that action parameters are defined: [jsonschema](http://json-schema.org/).


# Usage

Suppose layer `foo` specifies the following option definitions in its `layer.yaml`:

```yaml
defines:
  my_opt_1:
    description: A numerical option.
    type: number
    default: 1
  my_opt_a:
    description: An array option.
    type: array
    default: []
  my_opt_b:
    description: A boolean option.
    type: boolean
    default: false
```

A layer including it could specify values for these options in its own `layer.yaml`:

```yaml
options:
  foo:
    my_opt_1: 2
    my_opt_a: ['a', 'b']
    my_opt_b: true
```

The `foo` layer could then read these values in its reactive code:

```python
from charms import layer
from charms.reactive import when_not, set_flag


@when_not('layer.foo.done')
def do_foo():
    foo_opts = layer.options.get('foo')  # returns a dict of all the options
    my_opt_1 = layer.options.get('foo', 'my_opt_1')  # returns just that option
    do_something_with(foo_opts)
    set_flag('layer.foo.done')
```
