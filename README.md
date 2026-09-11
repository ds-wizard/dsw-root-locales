# `dsw:root` localization

This project provides localization files for the `dsw:root` package, enabling support for multiple languages and regions.

## Updating the source catalog

Place the compiled source Knowledge Model JSON in `scripts/km.json`, using the
KM version declared in `build_pot`. In a Python environment, run:

```sh
python -m pip install -r scripts/requirements.txt
python -m unittest discover -s scripts -p 'test_*.py'
python scripts/extract-messages.py
```

This updates the shared `messages.pot`; it does not modify any language PO.
Review its differences against DSW's native POT export for the same KM version.
After accepting a POT update, maintainers must arrange a merge into existing
language PO files, for example with Weblate's
[Update PO files to match POT](https://docs.weblate.org/en/latest/admin/addons.html#update-po-files-to-match-pot-msgmerge)
add-on. Preserve translations for unchanged sources and review changed or removed
sources. New sources add untranslated entries; do not replace a language PO with
the POT.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
