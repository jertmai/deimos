from wizwalker.extensions.wizsprinter.combat_backends.combat_api import TemplateSpell
import inspect

t = TemplateSpell([], False)
print(f"Attributes: {dir(t)}")
print(f"Vars: {vars(t)}")
