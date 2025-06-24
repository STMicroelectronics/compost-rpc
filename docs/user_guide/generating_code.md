# Generating code

The main strength of Compost is its ability to generate implementations of a
defined protocol in multiple languages from a single protocol definition file
written in Python. To achieve this, an instance of a protocol provides a
generator object that can be configured to generate source files for the
protocol implementation.

Typically, the generation process is specified within the protocol definition
file itself, so that when the file is executed as a script, the relevant output
is generated. The generator can also be used from any script that imports the
protocol definition as a library, although in such cases, it is more common to
use the defined protocol interface for communication rather than generating
code.

```{code-block} python
:caption: Simple code to generate C code for the ExampleProtocol

from st_python import rpc, U32, U8, Generator

class ExampleProtocol(Protocol):
    @rpc(0x001)
    def read8(address: U32) -> U8:
    """Reads 8 bits of data from the specified address"""

if __name__ == "__main__":
    import sys

    with Generator(ExampleProtocol) as gen:
        gen.c.generate()
```

Some generator settings are common across all languages, such as the output path
and filename. However, there are also language-specific settings. For example,
when generating C# code, it might be useful to specify the namespace of the
generated files, a setting that would not be applicable for C code. For the
complete list of language specific options, refer to the [Generator API
reference](#compost_rpc.Generator).

```{code-block} python
:caption: Generation of C# code with certain settings modified

if __name__ == "__main__":
    with Generator(ExampleProtocol) as gen:
    # Enable C# code generation
        gen.csharp.path = "./src"
        gen.csharp.namespace = "ST.ExampleApp.IO"
        gen.csharp.generate()
```

As is clear from the examples, the most convenient way to use
{class}`compost_rpc.Generator` is with the help of with-block. The instantiated
{class}`compost_rpc.Generator` contains individual
{class}`compost_rpc.CodeGenerator` instances that each have properties that
affect the output. After making adjustment to these settings, you can mark the
specific language for generation by calling
{func}`compost_rpc.CodeGenerator.generate`. Once the with-scope ends,
{func}`compost_rpc.Generator.run` will be called automatically and create all the
files, while giving user feedback in the terminal.

The with-block syntax is really just a syntactic sugar and the
{func}`compost_rpc.Generator.run` function can also be called manually, but only
if the with-block is not used.

```{code-block} python
:caption: Alternative code generation setup without `with` statement

if __name__ == "__main__":
    gen = Generator(ExampleProtocol)
    gen.c.path = "../example-fw/src"
    gen.csharp.path = "../example-gui/src"
    gen.csharp.namespace = "ST.ExampleApp.IO"
    gen.c.generate()
    gen.csharp.generate()
    gen.run() #explicit `run` call
```

The {func}`compost_rpc.Generator.run` function facilitates the actual file
creation. If you wish to use the generated output differently or create a
different interface for the process, you can capture the results of
{func}`compost_rpc.CodeGenerator.generate`. It does not matter if you use the
individual {class}`compost_rpc.CodeGenerator` properties that are part of the
{class}`compost_rpc.Generator`, or if you instantiate individual code generators
yourself. In either case, the result of the
{func}`compost_rpc.CodeGenerator.generate` is simply a list of file paths and
contents.

```{code-block} python
:caption: User-handled file creation

if __name__ == "__main__":
    c_gen = CCodeGenerator(ExampleProtocol)
    c_gen.path = "../example-fw/src"
    c_output : list[tuple[Path,str]] = c_gen.generate()
    for path, content in c_output:
        path.write_text(content)
```

## Naming Conventions

The generator aims to produce code that not only functions correctly but also
adheres to the naming conventions of the target language. To achieve this, it
modifies the names of variables and classes to match the target language's
conventions. For this process to work effectively, it is essential that all
names in the protocol definition file follow Python naming conventions, as this
is what the generator expects.

- **Classes**: `PascalCase`

  ```python
  @compost_struct
  class SensorData:
      pass
  ```

- **Methods and functions**: `snake_case`

  ```python
  @rpc(0xA01)
  def set_timeout(timeout_ms: U32) -> U8:
      pass
  ```

- **Variables, class members and arguments**: `snake_case`

  ```python
  data_value = 0
  ```

### Abbreviations

When using PascalCase and camelCase, abbreviations should not break the casing rules. For example, use `TmosProtocol` instead of `TMOSProtocol` and `deviceId` instead of `deviceID`.

```python
class TmosProtocol(Protocol):
    @rpc(0x001)
    def read_data(self, sensor_id: U8) -> list[U32]:
        """Reads data."""
```

### Enum Values

Enum values should not be prefixed with the enum name. This will be done
automatically for C by the generator.

```{code-block} python
:caption: Correct enum definition ✅

@compost_enum
class Color(I8, Enum):
    RED = 1
    GREEN = 2
    BLUE = 3
```

```{code-block} python
:caption: Incorrect enum definition ❌

@compost_enum
class Color(I8, Enum):
    COLOR_RED = 1
    COLOR_GREEN = 2
    COLOR_BLUE = 3
```
