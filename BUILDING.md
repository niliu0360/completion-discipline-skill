# Building the Red Skill package

Run from the Control Layer repository root:

```bash
python build/build_completion_skill.py \
  --output dist/completion-discipline \
  --zip dist/completion-discipline-0.2.0-beta.1.zip
```

The generated package is self-contained. Do not hand-edit generated runtime or schema files in the distribution repository; rebuild them from this source profile.
