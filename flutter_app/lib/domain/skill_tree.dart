/// The tree of the ranks: the data of the app becomes the picture.
///
/// The ranks are the nodes of the tree and the gates of a rank are the
/// paths that lead into it. Everything comes from the configuration of
/// the reward engine and from the state of the user: no node and no path
/// is written by hand.
library;

import 'rewards.dart';
import 'rewards_config.dart';

/// The place of the nodes on the canvas. The chain of the ranks runs from
/// left to right; the gates hang under it.
const double kRankPitch = 132.0;
const double kGatePitch = 34.0;
const double kMarginLeft = 96.0;
const double kMarginRight = 96.0;
const double kRankRow = 150.0;
const double kGateRow = 302.0;
const double kMarginTop = 92.0;
const double kMarginBottom = 74.0;

/// The radius of a node.
const double kRankRadius = 58.0;
const double kGateRadius = 17.0;

/// The states of a node and of a path.
class NodeState {
  const NodeState._();

  static const String reached = 'reached';
  static const String current = 'current';
  static const String next = 'next';
  static const String locked = 'locked';
  static const String met = 'met';
  static const String unmet = 'unmet';
  static const String open = 'open';
  static const String ready = 'ready';
}

/// One node of the tree: a rank, or one gate of a rank.
class TreeNode {
  const TreeNode({
    required this.id,
    required this.kind,
    required this.state,
    required this.label,
    required this.x,
    required this.y,
    this.titleKey = '',
    this.gateKey = '',
    this.required = 0,
    this.current = 0,
    this.satisfied = false,
  });

  final String id;
  final String kind;
  final String state;
  final String label;
  final double x;
  final double y;
  final String titleKey;
  final String gateKey;
  final int required;
  final int current;
  final bool satisfied;
}

/// One path of the tree: from a gate, or from a rank, into a rank.
class TreeEdge {
  const TreeEdge({required this.source, required this.target, required this.state});

  final String source;
  final String target;
  final String state;
}

/// The whole tree: the nodes, the paths and the size of the canvas.
class SkillTree {
  const SkillTree({
    required this.nodes,
    required this.edges,
    required this.width,
    required this.height,
    required this.current,
    required this.nextTitle,
  });

  final List<TreeNode> nodes;
  final List<TreeEdge> edges;
  final double width;
  final double height;
  final String current;
  final String? nextTitle;

  /// The node of a certain id.
  TreeNode? nodeOf(String id) {
    for (final TreeNode node in nodes) {
      if (node.id == id) return node;
    }
    return null;
  }
}

/// Build the tree of the ranks out of the data of the app.
SkillTree buildSkillTree({
  required List<MedalRecord> medals,
  required int musters,
  required List<String> reachedTitles,
  required RewardsConfig config,
  required String Function(String titleKey) titleName,
  required String Function(String gateKey) gateName,
}) {
  final TitleState state = titleState(
    medals: medals,
    musters: musters,
    reachedTitles: reachedTitles,
    config: config,
  );

  final List<TitleRule> titles = config.titles;
  final List<List<TitleGate>> gatesOf = titles
      .map(
        (TitleRule rule) => gatesForTitle(
          rule,
          medals: medals,
          musters: musters,
          reachedTitles: reachedTitles,
          config: config,
        ),
      )
      .toList();

  final List<TreeNode> nodes = <TreeNode>[];
  final List<TreeEdge> edges = <TreeEdge>[];
  final List<double> places = <double>[
    for (int index = 0; index < titles.length; index++) kMarginLeft + index * kRankPitch,
  ];

  double gateCursor = kMarginLeft;
  for (int index = 0; index < titles.length; index++) {
    final TitleRule rule = titles[index];
    final String nodeState = _rankState(rule.key, state);
    nodes.add(
      TreeNode(
        id: 'rank:${rule.key}',
        kind: 'rank',
        state: nodeState,
        label: titleName(rule.key),
        x: places[index],
        y: kRankRow,
        titleKey: rule.key,
      ),
    );

    for (final TitleGate gate in gatesOf[index]) {
      nodes.add(
        TreeNode(
          id: 'gate:${rule.key}:${gate.key}',
          kind: 'gate',
          state: gate.satisfied ? NodeState.met : NodeState.unmet,
          label: gateName(gate.key),
          x: gateCursor,
          y: kGateRow,
          titleKey: rule.key,
          gateKey: gate.key,
          required: gate.required,
          current: gate.current,
          satisfied: gate.satisfied,
        ),
      );
      gateCursor += kGatePitch;
      edges.add(
        TreeEdge(
          source: 'gate:${rule.key}:${gate.key}',
          target: 'rank:${rule.key}',
          state: gate.satisfied ? NodeState.open : NodeState.locked,
        ),
      );
    }

    if (index > 0) {
      final String below = titles[index - 1].key;
      String edgeState = NodeState.locked;
      if (nodeState == NodeState.reached || nodeState == NodeState.current) {
        edgeState = NodeState.open;
      } else if (nodeState == NodeState.next) {
        edgeState = NodeState.ready;
      }
      edges.add(
        TreeEdge(source: 'rank:$below', target: 'rank:${rule.key}', state: edgeState),
      );
    }
  }

  return SkillTree(
    nodes: nodes,
    edges: edges,
    width: places.isEmpty
        ? kMarginLeft + kMarginRight
        : (places.last + kMarginRight > gateCursor + kMarginRight
            ? places.last + kMarginRight
            : gateCursor + kMarginRight),
    height: kMarginTop + kGateRow + kMarginBottom,
    current: state.current,
    nextTitle: state.nextTitle,
  );
}

String _rankState(String key, TitleState state) {
  if (key == state.current) return NodeState.current;
  if (key == state.nextTitle) return NodeState.next;
  if (state.reached.contains(key)) return NodeState.reached;
  return NodeState.locked;
}
