"""
CLI for managing SensitiveAccessPolicy entries without Admin UI.

Usage examples:
  python manage.py sensitive_policies list
  python manage.py sensitive_policies add --department legal --role manager --field cnp --updated-by secops@haos
  python manage.py sensitive_policies remove --department legal --role manager --field cnp
  python manage.py sensitive_policies export --format yaml > policies.yaml
  python manage.py sensitive_policies import --file policies.yaml

Design notes:
  - Validates field against allowed choices on the model.
  - Upserts on `add` (unique on department+role+field).
  - Fails closed on invalid inputs; clear exit codes for automation.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from identity.policies import SensitiveAccessPolicy
import json
import sys

try:
    import yaml  # type: ignore
    HAS_YAML = True
except Exception:
    HAS_YAML = False


def _validate_field(field: str):
    allowed = {c[0] for c in SensitiveAccessPolicy.FIELD_CHOICES}
    if field not in allowed:
        raise CommandError(f"Invalid field '{field}'. Allowed: {sorted(list(allowed))}")


class Command(BaseCommand):
    help = "Manage sensitive access policies (list/add/remove/clear/import/export)"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='subcommand')

        # list
        subparsers.add_parser('list', help='List all policies')

        # add
        p_add = subparsers.add_parser('add', help='Add or update a policy')
        p_add.add_argument('--department', required=True)
        p_add.add_argument('--role', required=True)
        p_add.add_argument('--field', required=True)
        p_add.add_argument('--deny', action='store_true', help='Set policy to deny (default allow)')
        p_add.add_argument('--updated-by', default='', help='Operator identifier (email/name)')

        # remove
        p_remove = subparsers.add_parser('remove', help='Remove a single policy')
        p_remove.add_argument('--department', required=True)
        p_remove.add_argument('--role', required=True)
        p_remove.add_argument('--field', required=True)

        # clear
        p_clear = subparsers.add_parser('clear', help='Clear policies by optional scope (requires --yes)')
        p_clear.add_argument('--department')
        p_clear.add_argument('--role')
        p_clear.add_argument('--field')
        p_clear.add_argument('--yes', action='store_true', help='Confirm deletion')

        # export
        p_export = subparsers.add_parser('export', help='Export policies to stdout')
        p_export.add_argument('--format', choices=['json', 'yaml'], default='json')

        # import
        p_import = subparsers.add_parser('import', help='Import policies from file (upsert)')
        p_import.add_argument('--file', required=True)

    def handle(self, *args, **opts):
        sub = opts.get('subcommand')
        if not sub:
            raise CommandError("Missing subcommand. Use --help for usage.")

        if sub == 'list':
            return self._list()
        if sub == 'add':
            return self._add(opts)
        if sub == 'remove':
            return self._remove(opts)
        if sub == 'clear':
            return self._clear(opts)
        if sub == 'export':
            return self._export(opts)
        if sub == 'import':
            return self._import(opts)
        raise CommandError(f"Unknown subcommand: {sub}")

    def _list(self):
        rows = SensitiveAccessPolicy.objects.order_by('department', 'role', 'field')
        if not rows.exists():
            self.stdout.write("No policies defined.")
            return
        self.stdout.write("department,role,field,can_reveal,updated_by,updated_at")
        for r in rows:
            self.stdout.write(f"{r.department},{r.role},{r.field},{r.can_reveal},{r.updated_by},{r.updated_at.isoformat()}")

    def _add(self, opts):
        dept = opts['department'].strip()
        role = opts['role'].strip()
        field = opts['field'].strip()
        deny = bool(opts.get('deny'))
        updated_by = (opts.get('updated_by') or '').strip()

        if not dept or not role:
            raise CommandError("department and role are required and must be non-empty")
        _validate_field(field)

        obj, _created = SensitiveAccessPolicy.objects.get_or_create(
            department=dept, role=role, field=field,
            defaults={'can_reveal': not deny, 'updated_by': updated_by},
        )
        if not _created:
            obj.can_reveal = not deny
            obj.updated_by = updated_by
            obj.save()

        state = 'allow' if obj.can_reveal else 'deny'
        self.stdout.write(self.style.SUCCESS(f"Upserted: {dept}:{role} {state} {field}"))

    def _remove(self, opts):
        dept = opts['department'].strip()
        role = opts['role'].strip()
        field = opts['field'].strip()
        _validate_field(field)
        deleted, _ = SensitiveAccessPolicy.objects.filter(
            department=dept, role=role, field=field
        ).delete()
        if deleted:
            self.stdout.write(self.style.SUCCESS(f"Removed: {dept}:{role} {field}"))
        else:
            self.stdout.write("No matching policy found.")

    def _clear(self, opts):
        qs = SensitiveAccessPolicy.objects.all()
        dept = (opts.get('department') or '').strip()
        role = (opts.get('role') or '').strip()
        field = (opts.get('field') or '').strip()
        if dept:
            qs = qs.filter(department=dept)
        if role:
            qs = qs.filter(role=role)
        if field:
            _validate_field(field)
            qs = qs.filter(field=field)

        count = qs.count()
        if count == 0:
            self.stdout.write("Nothing to clear.")
            return
        if not opts.get('yes'):
            raise CommandError(f"Refusing to delete {count} policies without --yes")
        deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} policies."))

    def _export(self, opts):
        fmt = opts.get('format') or 'json'
        rows = list(SensitiveAccessPolicy.objects.order_by('department', 'role', 'field').values(
            'department', 'role', 'field', 'can_reveal', 'updated_by', 'updated_at', 'created_at'
        ))
        if fmt == 'json':
            json.dump(rows, sys.stdout, default=str, indent=2)
            sys.stdout.write("\n")
            return
        if fmt == 'yaml':
            if not HAS_YAML:
                raise CommandError("PyYAML not installed. Use --format json or install pyyaml.")
            yaml.safe_dump(rows, sys.stdout, sort_keys=False)
            return
        raise CommandError(f"Unsupported format: {fmt}")

    def _import(self, opts):
        path = opts['file']
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise CommandError(f"Failed to read file: {e}")

        data = None
        # Try JSON first
        try:
            data = json.loads(content)
        except Exception:
            if HAS_YAML:
                try:
                    data = yaml.safe_load(content)
                except Exception as e:
                    raise CommandError(f"Failed to parse as YAML: {e}")
            else:
                raise CommandError("Invalid JSON, and PyYAML not available to parse YAML.")

        if not isinstance(data, list):
            raise CommandError("Expected a list of policy objects")

        for row in data:
            if not isinstance(row, dict):
                raise CommandError("Invalid row in input (expected object)")
            for key in ['department', 'role', 'field']:
                if key not in row:
                    raise CommandError(f"Missing key '{key}' in input row: {row}")
            _validate_field(row['field'])

        with transaction.atomic():
            for row in data:
                dept = str(row['department']).strip()
                role = str(row['role']).strip()
                field = str(row['field']).strip()
                can = bool(row.get('can_reveal', True))
                updated_by = str(row.get('updated_by') or '').strip()
                obj, _created = SensitiveAccessPolicy.objects.get_or_create(
                    department=dept, role=role, field=field,
                    defaults={'can_reveal': can, 'updated_by': updated_by},
                )
                if not _created:
                    obj.can_reveal = can
                    obj.updated_by = updated_by
                    obj.save()

        self.stdout.write(self.style.SUCCESS(f"Imported {len(data)} policies"))
