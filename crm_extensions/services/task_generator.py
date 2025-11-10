"""
TaskGenerator Service

Creates tasks from various sources: checklist items, triggers, manual requests.
Handles task initialization with flows, assignments, and entity linking.
"""

import logging
from typing import Any, Dict, Optional
from django.db.models import Model
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class TaskGenerator:
    """
    Generates tasks from different sources.

    Sources:
    1. Checklist items (manual or automatic)
    2. Flow triggers (automatic on entity events)
    3. Manual triggers (UI button clicks)
    """

    @staticmethod
    def create_from_checklist_item(
        checklist_item: Model,
        assigned_user: Optional[User] = None,
        flow: Optional['FlowDefinition'] = None
    ) -> Optional['Task']:
        """
        Create task from a checklist item.

        Args:
            checklist_item: SongChecklistItem instance
            assigned_user: User to assign task to (optional)
            flow: FlowDefinition to attach (optional)

        Returns:
            Task: Created task or None if failed
        """
        from crm_extensions.models import Task

        try:
            # Get song from checklist item
            song = checklist_item.song if hasattr(checklist_item, 'song') else None
            if not song:
                logger.error(f"Checklist item {checklist_item.id} has no song")
                return None

            # Build task data
            task_data = {
                'title': checklist_item.name,
                'description': checklist_item.description or f"Complete: {checklist_item.name}",
                'song': song,
                'song_checklist_item': checklist_item,
                'source_stage': checklist_item.stage,
                'source_checklist_name': checklist_item.name,
                'status': 'todo',
                'priority': 2,  # Normal priority
                'task_type': 'general',
            }

            # Add flow if provided
            if flow:
                task_data['flow'] = flow
                # Set current step to first step
                first_step = flow.steps.order_by('order').first()
                if first_step:
                    task_data['current_flow_step'] = first_step

            # Create task
            task = Task.objects.create(**task_data)

            # Assign user if provided
            if assigned_user:
                from crm_extensions.models import TaskAssignment
                TaskAssignment.objects.create(
                    task=task,
                    user=assigned_user,
                    role='assignee'
                )

            logger.info(f"Created task {task.id} from checklist item '{checklist_item.name}'")
            return task

        except Exception as e:
            logger.error(f"Error creating task from checklist item {checklist_item.id}: {e}")
            return None

    @staticmethod
    def create_from_trigger(
        trigger: 'FlowTrigger',
        entity: Model,
        created_by: Optional[User] = None
    ) -> Optional['Task']:
        """
        Create task from automatic flow trigger.

        Args:
            trigger: FlowTrigger instance
            entity: Entity that triggered the flow (Work, Contract, etc.)
            created_by: User who caused the trigger (optional)

        Returns:
            Task: Created task or None if failed
        """
        from crm_extensions.models import Task
        from api.models import Department

        if not trigger.creates_task:
            logger.debug(f"Trigger '{trigger.name}' doesn't create tasks")
            return None

        try:
            config = trigger.task_config or {}

            # Resolve template strings in config
            resolved_config = TaskGenerator._resolve_templates(config, entity)

            # Build task data
            task_data = {
                'title': resolved_config.get('title_template', f"Task for {entity}"),
                'description': resolved_config.get('description_template', ''),
                'status': 'todo',
                'priority': resolved_config.get('priority', 2),
                'task_type': resolved_config.get('task_type', 'general'),
                'created_by': created_by,
            }

            # Link to entity
            entity_type = trigger.trigger_entity_type
            if entity_type:
                task_data[entity_type] = entity

            # Add department
            department_name = resolved_config.get('department')
            if department_name:
                try:
                    department = Department.objects.get(name__iexact=department_name)
                    task_data['department'] = department
                except Department.DoesNotExist:
                    logger.warning(f"Department '{department_name}' not found")

            # Add flow
            if trigger.flow:
                task_data['flow'] = trigger.flow
                first_step = trigger.flow.steps.order_by('order').first()
                if first_step:
                    task_data['current_flow_step'] = first_step

            # Create task
            task = Task.objects.create(**task_data)

            logger.info(
                f"Created task {task.id} ('{task.title}') from trigger '{trigger.name}' "
                f"for {entity_type} {entity.id}"
            )
            return task

        except Exception as e:
            logger.error(f"Error creating task from trigger '{trigger.name}': {e}")
            return None

    @staticmethod
    def create_from_manual_trigger(
        trigger: 'ManualTrigger',
        entity: Model,
        user: User,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Optional['Task']:
        """
        Create task from manual trigger (UI button click).

        Args:
            trigger: ManualTrigger instance
            entity: Entity the button was clicked on
            user: User who clicked the button
            context_data: Additional context data (e.g., deliverable type)

        Returns:
            Task: Created task or None if failed
        """
        from crm_extensions.models import Task, FlowDefinition
        from api.models import Department

        try:
            config = trigger.action_config or {}

            # Merge entity and context_data for template resolution
            template_context = {**context_data} if context_data else {}

            # Resolve templates
            resolved_config = TaskGenerator._resolve_templates(config, entity, template_context)

            # Build task data
            task_data = {
                'title': resolved_config.get('task_title_template', f"Task from {trigger.button_label}"),
                'description': resolved_config.get('description', ''),
                'status': 'todo',
                'priority': resolved_config.get('priority', 2),
                'task_type': resolved_config.get('task_type', 'general'),
                'created_by': user,
            }

            # Link to entity
            entity_type = trigger.entity_type
            if entity_type:
                task_data[entity_type] = entity

            # Add department
            target_dept = resolved_config.get('target_department')
            if target_dept:
                try:
                    department = Department.objects.get(name__iexact=target_dept)
                    task_data['department'] = department
                except Department.DoesNotExist:
                    logger.warning(f"Department '{target_dept}' not found")

            # Add flow
            flow_name = resolved_config.get('flow')
            if flow_name:
                try:
                    flow = FlowDefinition.objects.get(name=flow_name, is_active=True)
                    task_data['flow'] = flow
                    first_step = flow.steps.order_by('order').first()
                    if first_step:
                        task_data['current_flow_step'] = first_step
                except FlowDefinition.DoesNotExist:
                    logger.warning(f"Flow '{flow_name}' not found")

            # Create task
            task = Task.objects.create(**task_data)

            logger.info(
                f"Created task {task.id} ('{task.title}') from manual trigger '{trigger.button_label}' "
                f"by user {user.id}"
            )
            return task

        except Exception as e:
            logger.error(f"Error creating task from manual trigger '{trigger.button_label}': {e}")
            return None

    @staticmethod
    def _resolve_templates(
        config: Dict[str, Any],
        entity: Model,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Resolve template strings in config.

        Template format: {entity.field_name} or {context_key}
        Example: "Handle contract for {work.name}" -> "Handle contract for Casa"

        Args:
            config: Configuration dictionary with template strings
            entity: Entity for field resolution
            context: Additional context variables

        Returns:
            dict: Config with resolved templates
        """
        resolved = {}

        for key, value in config.items():
            if isinstance(value, str):
                resolved[key] = TaskGenerator._resolve_string(value, entity, context)
            else:
                resolved[key] = value

        return resolved

    @staticmethod
    def _resolve_string(
        template: str,
        entity: Model,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Resolve a single template string.

        Args:
            template: Template string
            entity: Entity for field resolution
            context: Additional context

        Returns:
            str: Resolved string
        """
        import re

        # Find all {xxx.yyy} or {xxx} patterns
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, template)

        resolved = template

        for match in matches:
            try:
                # Check if it's a nested field (entity.field)
                if '.' in match:
                    parts = match.split('.')
                    obj = entity
                    for part in parts:
                        if hasattr(obj, part):
                            obj = getattr(obj, part)
                        else:
                            obj = f'{{{match}}}'  # Keep original if not found
                            break
                    resolved = resolved.replace(f'{{{match}}}', str(obj))

                # Check context
                elif context and match in context:
                    resolved = resolved.replace(f'{{{match}}}', str(context[match]))

                # Check direct entity field
                elif hasattr(entity, match):
                    value = getattr(entity, match)
                    resolved = resolved.replace(f'{{{match}}}', str(value))

            except Exception as e:
                logger.debug(f"Error resolving template variable '{match}': {e}")
                # Keep original if resolution fails

        return resolved
