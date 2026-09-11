"""Pure renderers for story guidance, authoring, and transition assessment."""

from .assessment import (
    build_story_assessment_system_section,
    build_story_assessment_user_section,
)
from .author import (
    AUTHOR_COMPILER_TEMPLATE,
    build_story_author_system_section,
    build_story_author_user_section,
)
from .context import StoryGuidanceContext, StoryGuidanceTransition, StoryRequestContext
from .guidance import build_story_guidance_section

__all__ = [
    "AUTHOR_COMPILER_TEMPLATE",
    "StoryGuidanceContext",
    "StoryGuidanceTransition",
    "StoryRequestContext",
    "build_story_guidance_section",
    "build_story_author_system_section",
    "build_story_author_user_section",
    "build_story_assessment_system_section",
    "build_story_assessment_user_section",
]
