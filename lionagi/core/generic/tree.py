"""This module provides tree structure."""

from pydantic import Field
from lionagi.core.collections.abc import Condition
from lionagi.core.collections.util import to_list_type
from lionagi.core.generic.tree_node import TreeNode
from lionagi.core.generic.graph import Graph

from typing_extensions import deprecated

from lionagi.os.sys_utils import format_deprecated_msg


@deprecated(
    format_deprecated_msg(
        deprecated_name="lionagi.core.action.function_calling.FunctionCalling",
        deprecated_version="v0.3.0",
        removal_version="v1.0",
        replacement="check `lion-core` package for updates",
    ),
    category=DeprecationWarning,
)
class Tree(Graph):
    """
    Represents a tree structure, extending the graph with tree-specific functionalities.

    Manages parent-child relationships within the tree.

    Attributes:
        root (TreeNode | None): The root node of the tree. Defaults to None.
    """

    root: TreeNode | None = Field(
        default=None, description="The root node of the tree graph."
    )

    def relate_parent_child(
        self,
        parent: TreeNode,
        children,
        condition: Condition | None = None,
        bundle: bool = False,
    ) -> None:
        """
        Establishes parent-child relationships between the given parent and child node(s).

        Args:
            parent (TreeNode): The parent node.
            children (list[TreeNode]): A list of child nodes.
            condition (Condition | None): The condition associated with the relationships, if any.
            bundle (bool): Indicates whether to bundle the relations into a single
                           transaction. Defaults to False.
        """

        for i in to_list_type(children):
            i.relate_parent(parent, condition=condition, bundle=bundle)

        if self.root is None:
            self.root = parent

        self.add_node([parent, *children])
