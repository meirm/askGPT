"""Comprehensive typing compatibility fix for OpenAI SDK with openai-agents library.

This fix is necessary because:
1. OpenAI SDK >=1.99.2 changed several TypedDict types to Union types
2. The openai-agents library tries to instantiate these Union types directly
3. Union types cannot be instantiated in Python

This will be unnecessary once openai-agents updates to handle the new type structure.
"""

import logging
import sys

logger = logging.getLogger(__name__)


def apply_patches():
    """Replace problematic Union types with concrete types for compatibility."""

    # Only apply once
    if hasattr(sys, "_openai_typing_patched"):
        return

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


# Auto-apply patches on import
apply_patches()
