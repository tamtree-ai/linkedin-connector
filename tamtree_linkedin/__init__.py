"""Tamtree LinkedIn connector — personal-profile text posts."""

from tamtree_linkedin.credentials import LINKEDIN_API
from tamtree_linkedin.nodes import LinkedInCreatePostNode

NODES = [LinkedInCreatePostNode()]

__all__ = ["LINKEDIN_API", "NODES", "LinkedInCreatePostNode"]
