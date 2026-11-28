/// The drawing of the tree of the ranks.
///
/// The tree is painted by the code: the ranks are the shields of the
/// badges, the gates are the small medallions that hang under them, and
/// the paths between them are the gold of the road that has been walked
/// and the grey of the road that has not.
///
/// The state of a node is told three times over: by the words in the
/// tooltip, by the shape of the rim, and by the colour — never by the
/// colour alone.
library;

import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../domain/skill_tree.dart';
import '../theme.dart';

/// The tree of the ranks, painted on a canvas that scrolls sideways.
class SkillTreeView extends StatelessWidget {
  const SkillTreeView({
    super.key,
    required this.tree,
    required this.palette,
    required this.onNodeTap,
    this.selectedId,
  });

  final SkillTree tree;
  final AppPalette palette;
  final ValueChanged<TreeNode> onNodeTap;
  final String? selectedId;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final double scale = math.min(1.0, constraints.maxWidth / tree.width);
        final double width = tree.width * scale;
        final double height = tree.height * scale;
        return SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: SizedBox(
            width: width,
            height: height,
            child: GestureDetector(
              onTapUp: (TapUpDetails details) {
                final double x = details.localPosition.dx / scale;
                final double y = details.localPosition.dy / scale;
                TreeNode? hit;
                double best = double.infinity;
                for (final TreeNode node in tree.nodes) {
                  final double dx = node.x - x;
                  final double dy = node.y - y;
                  final double distance = math.sqrt(dx * dx + dy * dy);
                  final double reach = node.kind == 'rank' ? kRankRadius : kGateRadius * 1.6;
                  if (distance < reach && distance < best) {
                    best = distance;
                    hit = node;
                  }
                }
                if (hit != null) onNodeTap(hit);
              },
              child: CustomPaint(
                painter: SkillTreePainter(tree: tree, palette: palette, scale: scale),
              ),
            ),
          ),
        );
      },
    );
  }
}

/// The painter of the tree.
class SkillTreePainter extends CustomPainter {
  SkillTreePainter({required this.tree, required this.palette, required this.scale});

  final SkillTree tree;
  final AppPalette palette;
  final double scale;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(scale);
    _paintFloor(canvas);
    _paintEdges(canvas);
    _paintGates(canvas);
    _paintRanks(canvas);
    canvas.restore();
  }

  /// The dark field the picture stands on.
  void _paintFloor(Canvas canvas) {
    final Rect field = Rect.fromLTWH(0, 0, tree.width, tree.height);
    final Paint paint = Paint()
      ..shader = RadialGradient(
        center: const Alignment(0, -0.4),
        radius: 0.95,
        colors: <Color>[palette.floorOne, palette.floorTwo, palette.floorThree],
        stops: const <double>[0, 0.6, 1],
      ).createShader(field);
    canvas.drawRect(field, paint);
  }

  /// The roads of the tree.
  void _paintEdges(Canvas canvas) {
    for (final TreeEdge edge in tree.edges) {
      final TreeNode? source = tree.nodeOf(edge.source);
      final TreeNode? target = tree.nodeOf(edge.target);
      if (source == null || target == null) continue;

      final bool isOpen =
          edge.state == NodeState.open || edge.state == NodeState.ready;
      final Color colour = isOpen ? palette.gilt : palette.iron;
      final double width = isOpen ? 7 : 4;

      final Path road = Path();
      if (source.kind == 'rank' && target.kind == 'rank') {
        final double x1 = source.x + kRankRadius - 6;
        final double x2 = target.x - kRankRadius + 6;
        final double middle = (x1 + x2) / 2;
        road.moveTo(x1, source.y);
        road.cubicTo(middle, source.y - 14, middle, target.y + 14, x2, target.y);
      } else {
        road.moveTo(source.x, source.y - kGateRadius - 3);
        road.lineTo(target.x, target.y + kRankRadius - 6);
      }

      canvas.drawPath(
        road,
        Paint()
          ..color = Colors.black.withValues(alpha: 0.55)
          ..style = PaintingStyle.stroke
          ..strokeWidth = width + 4
          ..strokeCap = StrokeCap.round,
      );
      canvas.drawPath(
        road,
        Paint()
          ..color = colour
          ..style = PaintingStyle.stroke
          ..strokeWidth = width
          ..strokeCap = StrokeCap.round,
      );
    }
  }

  /// The gates: the small medallions that hang under the ranks.
  void _paintGates(Canvas canvas) {
    for (final TreeNode node in tree.nodes) {
      if (node.kind != 'gate') continue;
      final bool met = node.satisfied;
      final Color rim = met ? palette.gilt : palette.iron;

      canvas.drawCircle(
        Offset(node.x, node.y),
        kGateRadius + 2,
        Paint()..color = palette.floorThree,
      );
      canvas.drawCircle(
        Offset(node.x, node.y),
        kGateRadius - 2,
        Paint()
          ..color = met
              ? Color.alphaBlend(palette.gilt.withValues(alpha: 0.14), palette.floorThree)
              : palette.floorThree,
      );
      canvas.drawCircle(
        Offset(node.x, node.y),
        kGateRadius - 2,
        Paint()
          ..color = rim
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.5,
      );
      _paintGateGlyph(canvas, node, rim);
      _paintText(
        canvas,
        node.label,
        Offset(node.x, node.y + kGateRadius + 15),
        fontSize: 12,
        color: palette.ink.withValues(alpha: 0.75),
      );
      _paintText(
        canvas,
        '${node.current}/${node.required}',
        Offset(node.x, node.y + kGateRadius + 29),
        fontSize: 11,
        color: palette.ink.withValues(alpha: 0.55),
      );
    }
  }

  /// The mark of a gate.
  void _paintGateGlyph(Canvas canvas, TreeNode node, Color colour) {
    final Paint paint = Paint()
      ..color = colour
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.6
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    final Offset centre = Offset(node.x, node.y);

    switch (node.gateKey) {
      case 'degrees':
        for (int index = 0; index < 3; index++) {
          final double y = centre.dy - 6 + index * 7;
          canvas.drawPath(
            Path()
              ..moveTo(centre.dx - 8, y)
              ..lineTo(centre.dx, y - 3)
              ..lineTo(centre.dx + 8, y),
            paint,
          );
        }
      case 'musters':
        for (int index = 0; index < 7; index++) {
          final double angle = -math.pi / 2 + 2 * math.pi * index / 7;
          canvas.drawCircle(
            Offset(centre.dx + 9 * math.cos(angle), centre.dy + 9 * math.sin(angle)),
            2,
            Paint()..color = colour,
          );
        }
      case 'silver':
        canvas.drawArc(
          Rect.fromCircle(center: centre, radius: 9),
          math.pi / 2,
          math.pi * 1.5,
          false,
          paint,
        );
      case 'gold':
        canvas.drawCircle(centre, 5, paint);
        for (int index = 0; index < 8; index++) {
          final double angle = math.pi / 8 + 2 * math.pi * index / 8;
          canvas.drawLine(
            Offset(centre.dx + 8 * math.cos(angle), centre.dy + 8 * math.sin(angle)),
            Offset(centre.dx + 11 * math.cos(angle), centre.dy + 11 * math.sin(angle)),
            paint,
          );
        }
      case 'virtues':
        canvas.drawCircle(Offset(centre.dx - 5, centre.dy), 5.5, paint);
        canvas.drawCircle(Offset(centre.dx + 5, centre.dy), 5.5, paint);
      case 'fiefs':
        canvas.drawPath(
          Path()
            ..moveTo(centre.dx - 7, centre.dy + 9)
            ..lineTo(centre.dx - 7, centre.dy - 4)
            ..lineTo(centre.dx - 3.5, centre.dy - 4)
            ..lineTo(centre.dx - 3.5, centre.dy - 8)
            ..lineTo(centre.dx, centre.dy - 8)
            ..lineTo(centre.dx, centre.dy - 4)
            ..lineTo(centre.dx + 3.5, centre.dy - 4)
            ..lineTo(centre.dx + 3.5, centre.dy - 8)
            ..lineTo(centre.dx + 7, centre.dy - 8)
            ..lineTo(centre.dx + 7, centre.dy + 9),
          paint,
        );
      case 'vigil':
        canvas.drawPath(
          Path()
            ..moveTo(centre.dx, centre.dy - 10)
            ..cubicTo(
              centre.dx + 5,
              centre.dy - 4,
              centre.dx + 7,
              centre.dy,
              centre.dx + 7,
              centre.dy + 4,
            )
            ..arcToPoint(
              Offset(centre.dx - 7, centre.dy + 4),
              radius: const Radius.circular(7),
              clockwise: true,
            )
            ..cubicTo(
              centre.dx - 7,
              centre.dy,
              centre.dx - 5,
              centre.dy - 4,
              centre.dx,
              centre.dy - 10,
            ),
          paint,
        );
      default:
        if (node.gateKey.startsWith('virtue:')) {
          canvas.drawPath(
            Path()
              ..moveTo(centre.dx - 4.5, centre.dy - 9)
              ..lineTo(centre.dx + 4.5, centre.dy - 9)
              ..lineTo(centre.dx + 4.5, centre.dy + 5)
              ..lineTo(centre.dx, centre.dy + 10)
              ..lineTo(centre.dx - 4.5, centre.dy + 5)
              ..close(),
            paint,
          );
        }
    }
  }

  /// The ranks: the shield of the badge inside a rim.
  void _paintRanks(Canvas canvas) {
    for (final TreeNode node in tree.nodes) {
      if (node.kind != 'rank') continue;
      final bool locked = node.state == NodeState.locked;
      final bool isCurrent = node.state == NodeState.current;
      final Offset centre = Offset(node.x, node.y);

      if (isCurrent) {
        canvas.drawCircle(
          centre,
          kRankRadius + 8,
          Paint()
            ..color = palette.accent.withValues(alpha: 0.28)
            ..style = PaintingStyle.stroke
            ..strokeWidth = 2,
        );
      }

      canvas.drawCircle(centre, kRankRadius - 2, Paint()..color = palette.floorThree);
      canvas.drawCircle(
        centre,
        kRankRadius,
        Paint()
          ..color = locked ? palette.iron : palette.gilt
          ..style = PaintingStyle.stroke
          ..strokeWidth = isCurrent ? 4 : 3,
      );

      // The twelve notches of the frame, the same look the web app draws.
      final Paint notchPaint = Paint()
        ..color = locked ? palette.iron : palette.gilt
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3
        ..strokeCap = StrokeCap.round;
      const double inner = kRankRadius - 9;
      const double outer = kRankRadius;
      for (int index = 0; index < 12; index++) {
        final double angle = (math.pi * 2 * index) / 12;
        canvas.drawLine(
          Offset(centre.dx + inner * math.cos(angle), centre.dy + inner * math.sin(angle)),
          Offset(centre.dx + outer * math.cos(angle), centre.dy + outer * math.sin(angle)),
          notchPaint,
        );
      }

      _paintShield(canvas, node, centre, locked);
      _paintText(
        canvas,
        node.label,
        Offset(node.x, node.y - kRankRadius - 14),
        fontSize: 15,
        color: palette.ink.withValues(alpha: locked ? 0.55 : 0.95),
      );
    }
  }

  /// The shield of the badge of a title.
  void _paintShield(Canvas canvas, TreeNode node, Offset centre, bool locked) {
    const double scale = 0.52;
    canvas.save();
    canvas.translate(centre.dx - 50 * scale, centre.dy - 60 * scale);
    canvas.scale(scale);

    final Paint field = Paint()..color = locked ? palette.iron.withValues(alpha: 0.35) : _tincture(node.titleKey);
    final Path shield = Path()
      ..moveTo(14, 30)
      ..lineTo(86, 30)
      ..lineTo(86, 60)
      ..cubicTo(86, 85, 68, 103, 50, 112)
      ..cubicTo(32, 103, 14, 85, 14, 60)
      ..close();
    canvas.drawPath(shield, field);
    canvas.drawPath(
      shield,
      Paint()
        ..color = locked ? palette.iron : palette.gilt
        ..style = PaintingStyle.stroke
        ..strokeWidth = 6,
    );

    final Paint charge = Paint()
      ..color = locked ? palette.iron.withValues(alpha: 0.6) : palette.ink.withValues(alpha: 0.9)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 6
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(
      Path()
        ..moveTo(36, 74)
        ..lineTo(64, 74)
        ..moveTo(50, 48)
        ..lineTo(50, 92),
      charge,
    );
    canvas.restore();
  }

  /// The colour of the field of a title.
  Color _tincture(String key) {
    switch (key) {
      case 'page':
        return const Color(0xFF2B2118);
      case 'squire':
        return const Color(0xFF1E3A5F);
      case 'knight':
        return const Color(0xFF6E1F1F);
      case 'banneret':
        return const Color(0xFF1F4A2E);
      case 'baron':
        return const Color(0xFF3B2350);
      case 'viscount':
        return const Color(0xFF1E3A5F);
      case 'earl':
        return const Color(0xFF6E1F1F);
      case 'marquess':
        return const Color(0xFF1F4A2E);
      case 'duke':
        return const Color(0xFF3B2350);
      case 'prince':
        return const Color(0xFF1E3A5F);
      case 'king':
        return const Color(0xFF6E1F1F);
      default:
        return const Color(0xFF2B2118);
    }
  }

  /// A word of the picture.
  void _paintText(
    Canvas canvas,
    String text,
    Offset centre, {
    required double fontSize,
    required Color color,
  }) {
    final TextPainter painter = TextPainter(
      text: TextSpan(
        text: text,
        style: TextStyle(
          color: color,
          fontSize: fontSize,
          fontWeight: FontWeight.w600,
          height: 1.1,
        ),
      ),
      textDirection: TextDirection.rtl,
      textAlign: TextAlign.center,
    )..layout();
    painter.paint(canvas, Offset(centre.dx - painter.width / 2, centre.dy - painter.height / 2));
  }

  @override
  bool shouldRepaint(covariant SkillTreePainter oldDelegate) =>
      oldDelegate.tree != tree || oldDelegate.palette != palette;
}
