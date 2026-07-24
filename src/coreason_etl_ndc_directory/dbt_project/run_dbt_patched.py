import sys

# --- Ultimate Monkey Patch for Pydantic V1 / Python 3.14 ---
try:
    import pydantic.v1.validators as validators
    import pydantic.v1.fields as fields
    import pydantic.v1.errors as errors_

    # Patch 1: Bypass FieldInfo validation errors
    original_find_validators = validators.find_validators
    def patched_find_validators(type_, config):
        try:
            yield from original_find_validators(type_, config)
        except RuntimeError as e:
            if "no validator found for" in str(e) and "FieldInfo" in str(type_):
                yield lambda v: v
            else:
                raise
    
    validators.find_validators = patched_find_validators
    fields.find_validators = patched_find_validators

    # Patch 2: Bypass missing type annotations for default_factory
    original_set_default_and_type = fields.ModelField._set_default_and_type
    def patched_set_default_and_type(self):
        try:
            original_set_default_and_type(self)
        except errors_.ConfigError as e:
            if "default_factory" in str(e):
                # If Python 3.14 drops the type hint, infer it from the factory itself
                fallback_type = self.default_factory if self.default_factory in (list, dict, set) else str
                self.type_ = fallback_type
                self.outer_type_ = fallback_type
            else:
                raise
                
    fields.ModelField._set_default_and_type = patched_set_default_and_type

except ImportError:
    pass
# -----------------------------------------------------------

# Import and execute the dbt CLI
from dbt.cli.main import cli

if __name__ == '__main__':
    sys.exit(cli(sys.argv[1:]))
