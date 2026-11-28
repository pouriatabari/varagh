/// The court chart of the Flutter app: the pyramid of the titles.
///
/// The ladder of the titles is drawn as a pyramid: the king at the top,
/// the page at the bottom, and the tier of the user the one that shines.
/// A small badge stands beside every tier, so the ladder reads at a
/// glance — the eye finds the lit tier and the next one below.
library;

import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../domain/rewards_config.dart';
import '../domain/skill_tree.dart';
import '../theme.dart';

/// The court chart of the user.
class CourtChartView extends StatelessWidget {
  const CourtChartView({
    super.key,
    required this.tree,
    required this.config,
    required this.palette,
    required this.onTap,
    this.selectedKey,
  });

  final SkillTree tree;
  final RewardsConfig config;
  final AppPalette palette;
  final ValueChanged<TreeNode> onTap;
  final String? selectedKey;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        const double rowHeight = 34;
        const double width = 380;
        final List<TreeNode> ranks = tree.nodes
            .where((TreeNode node) => node.kind == 'rank')
            .toList();
        final double height = ranks.length * rowHeight + 16;
        return GestureDetector(
          onTapUp: (TapUpDetails details) {
            final int index = ((details.localPosition.dy - 8) / rowHeight).floor();
            if (index >= 0 && index < ranks.length) {
              onTap(ranks[ranks.length - 1 - index]);
            }
          },
          child: SizedBox(
            width: width.toDouble(),
            height: height,
            child: CustomPaint(
              painter: CourtChartPainter(
                ranks: ranks.reversed.toList(),
                palette: palette,
                selectedKey: selectedKey,
              ),
            ),
          ),
        );
      },
    );
  }
}

/// The painter of the court chart.
class CourtChartPainter extends CustomPainter {
  CourtChartPainter({
    required this.ranks,
    required this.palette,
    this.selectedKey,
  });

  final List<TreeNode> ranks;
  final AppPalette palette;
  final String? selectedKey;

  static const double _width = 380.0;
  static const double _rowHeight = 34.0;

  Color get _litFill => palette.accent;
  Color get _lockedFill => palette.elevated;
  Color get _stroke => palette.border;

  @override
  void paint(Canvas canvas, Size size) {
    final int count = ranks.length;
    final double topHalf = _width * 0.15;
    final double bottomHalf = _width * 0.42;
    final double span = (bottomHalf - topHalf) / math.max(count, 1);
    final double middle = _width / 2;

    for (int index = 0; index < count; index++) {
      final TreeNode tier = ranks[index];
      final double halfTop = topHalf + span * index;
      final double halfBottom = halfTop + span;
      final double y = 8 + index * _rowHeight;
      final bool reached = tier.state == NodeState.reached ||
          tier.state == NodeState.current;
      final bool current = tier.state == NodeState.current;
      final bool next = tier.state == NodeState.next;

      final Color fill = reached ? _litFill : _lockedFill;
      final Path trapezoid = Path()
        ..moveTo(middle - halfTop, y)
        ..lineTo(middle + halfTop, y)
        ..lineTo(middle + halfBottom, y + _rowHeight - 3)
        ..lineTo(middle - halfBottom, y + _rowHeight - 3)
        ..close();
      canvas.drawPath(
        trapezoid,
        Paint()
          ..color = fill.withValues(alpha: reached ? 0.95 : 0.4)
          ..style = PaintingStyle.fill,
      );
      canvas.drawPath(
        trapezoid,
        Paint()
          ..color = current
              ? palette.accentTwo
              : next
                  ? palette.accent.withValues(alpha: 0.6)
                  : _stroke
          ..style = PaintingStyle.stroke
          ..strokeWidth = current ? 2 : 1,
      );

      _paintLabel(canvas, tier, middle, y);
    }
  }

  void _paintLabel(Canvas canvas, TreeNode tier, double middle, double y) {
    final TextPainter painter = TextPainter(
      text: TextSpan(
        text: tier.label,
        style: TextStyle(
          color: tier.state == NodeState.locked
              ? palette.muted
              : palette.ink.withValues(alpha: 0.92),
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
      ),
      textDirection: TextDirection.rtl,
      textAlign: TextAlign.center,
    )..layout(maxWidth: 280);
    painter.paint(
      canvas,
      Offset(
        middle - painter.width / 2,
        y + _rowHeight / 2 - painter.height / 2,
      ),
    );
  }

  @override
  bool shouldRepaint(covariant CourtChartPainter oldDelegate) =>
      oldDelegate.ranks != ranks || oldDelegate.palette != palette;
}
