"""Comprehensive typing compatibility fix for OpenAI SDK with openai-agents library.

This fix is necessary because:
1. OpenAI SDK >=1.99.2 changed several TypedDict types to Union types
2. The openai-agents library tries to instantiate these Union types directly
3. Union types cannot be instantiated in Python
4. openai-agents 0.2.7 tries to import openai.types.responses.response_prompt_param
   which doesn't exist in OpenAI SDK 1.10.0

This will be unnecessary once openai-agents updates to handle the new type structure.
"""

import logging
import sys
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def apply_patches():
    """Replace problematic Union types with concrete types for compatibility."""

    # Only apply once
    if hasattr(sys, "_openai_typing_patched"):
        return

    # First, fix the missing response_prompt_param module issue
    # This must happen BEFORE agents is imported
    try:
        import openai
        
        # Fix missing NOT_GIVEN constant
        if not hasattr(openai, 'NOT_GIVEN'):
            # NOT_GIVEN is a sentinel value used in OpenAI SDK
            # Create a simple sentinel object
            class _NotGiven:
                """Sentinel value for NOT_GIVEN."""
                def __repr__(self):
                    return "NOT_GIVEN"
            
            openai.NOT_GIVEN = _NotGiven()
            logger.debug("Created missing NOT_GIVEN compatibility shim")
        
        import openai.types as types_module
        
        # Create responses submodule if it doesn't exist
        if not hasattr(types_module, 'responses'):
            import types
            responses_module = types.ModuleType('responses')
            # Mark as a package so submodules can be imported
            responses_module.__path__ = []
            setattr(types_module, 'responses', responses_module)
            # Add to sys.modules so imports work
            sys.modules['openai.types.responses'] = responses_module
        
        responses_module = getattr(types_module, 'responses')
        
        # Create a function to dynamically create missing submodules
        def create_response_submodule(name):
            """Create a missing response submodule."""
            full_name = f'openai.types.responses.{name}'
            if full_name not in sys.modules:
                import types
                submodule = types.ModuleType(name)
                # Don't set __path__ for non-package modules
                setattr(responses_module, name, submodule)
                sys.modules[full_name] = submodule
                logger.debug(f"Created submodule: {full_name}")
                return submodule
            return sys.modules[full_name]
        
        # Create all known submodules that openai-agents needs
        submodules = [
            'response_prompt_param',
            'response_code_interpreter_tool_call',
            'response_file_search_tool_call',
            'response_function_tool_call',
            'response_input_item_param',
            'response_output_item',
            'response_reasoning_item',
        ]
        
        # Define classes needed for each submodule
        submodule_classes = {
            'response_code_interpreter_tool_call': ['ResponseCodeInterpreterToolCall'],
            'response_file_search_tool_call': ['ResponseFileSearchToolCall'],
            'response_function_tool_call': ['ResponseFunctionToolCall'],
            'response_input_item_param': [
                'ComputerCallOutput',
                'FunctionCallOutput',
                'LocalShellCallOutput',
                'McpApprovalResponse',
            ],
            'response_output_item': ['ResponseOutputItem'],
            'response_reasoning_item': ['ResponseReasoningItem'],
        }
        
        for submodule_name in submodules:
            submodule = create_response_submodule(submodule_name)
            
            # Add classes expected in this submodule
            classes_to_add = submodule_classes.get(submodule_name, [])
            for class_name in classes_to_add:
                if not hasattr(submodule, class_name):
                    class_dict = {'__module__': f'openai.types.responses.{submodule_name}'}
                    placeholder = type(class_name, (dict,), class_dict)
                    setattr(submodule, class_name, placeholder)
                    logger.debug(f"Created {class_name} in {submodule_name}")
        
        response_prompt_param_module = getattr(responses_module, 'response_prompt_param')
        
        # Create ResponsePromptParam class if it doesn't exist
        if not hasattr(response_prompt_param_module, 'ResponsePromptParam'):
            from typing import TypedDict, Union, List, Dict, Any
            
            # ResponsePromptParam is typically a Union of string or list of strings
            # For compatibility with openai-agents, we'll make it a type alias
            ResponsePromptParam = Union[str, List[str], Dict[str, Any]]
            
            setattr(response_prompt_param_module, 'ResponsePromptParam', ResponsePromptParam)
            logger.debug("Created missing ResponsePromptParam compatibility shim")
        
        # Add all response types that openai-agents expects
        # These are placeholders - the actual types may vary
        missing_types = [
            'Response',
            'ResponseComputerToolCall',
            'ResponseFileSearchToolCall',
            'ResponseFunctionToolCall',
            'ResponseFunctionWebSearch',
            'ResponseInputItemParam',
            'ResponseMessage',
            'ResponseMessageToolCall',
            'ResponseOutputItem',
            'ResponseOutputMessage',
            'ResponseOutputRefusal',
            'ResponseOutputText',
            'ResponseStreamEvent',
        ]
        
        for type_name in missing_types:
            if not hasattr(responses_module, type_name):
                # Create a simple TypedDict placeholder
                from typing import TypedDict, Any as AnyType
                
                # Create a generic TypedDict class
                class_dict = {'__module__': 'openai.types.responses', '__qualname__': type_name}
                placeholder_type = type(type_name, (dict,), class_dict)
                setattr(responses_module, type_name, placeholder_type)
                logger.debug(f"Created missing {type_name} compatibility shim")
            
    except Exception as e:
        logger.debug(f"Could not create ResponsePromptParam shim: {e}")

    try:
        # Import the chat module and typing utilities
        from typing import Union, get_origin

        import openai.types as types_module
        import openai.types.chat as chat_module
        # Import concrete types to use as replacements
        from openai.types.chat import (
            ChatCompletionAssistantMessageParam,
            ChatCompletionFunctionToolParam,
            ChatCompletionMessageFunctionToolCallParam)

        # List of patches to apply (Union type name -> concrete type to use)
        patches = {
            "ChatCompletionMessageToolCallParam": ChatCompletionMessageFunctionToolCallParam,
            # Add more patches here if other Union types cause issues
        }

        # Apply patches
        for attr_name, replacement in patches.items():
            if hasattr(chat_module, attr_name):
                original = getattr(chat_module, attr_name)
                # Only patch if it's actually a Union type
                if get_origin(original) is Union:
                    setattr(chat_module, attr_name, replacement)
                    # Also update in parent module's namespace
                    if hasattr(types_module, "chat"):
                        setattr(types_module.chat, attr_name, replacement)
                    logger.debug(
                        f"Patched {attr_name} from Union to {replacement.__name__}"
                    )

        # Mark as patched
        sys._openai_typing_patched = True
        logger.debug("OpenAI typing patches applied successfully")

    except ImportError as e:
        # OpenAI SDK not installed or different version structure
        logger.debug(f"Could not apply OpenAI typing patches: {e}")
    except Exception as e:
        # Log but don't fail - the patches are a workaround
        logger.debug(f"Error applying OpenAI typing patches: {e}")


# Auto-apply patches on import (must happen before agents is imported)
apply_patches()
