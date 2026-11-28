/// The map of the realms, painted from the vendored ground.
///
/// The ground of the map is a file of paths that never changes; the state
/// of every realm is drawn on top of it: the fog over the realm that is
/// still unknown, the hatch over the hidden one, the gold of the realm
/// that is won.
library;

import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../data/realms.dart';
import '../theme.dart';

/// The ground of the map: the sea, the coast and the realms.
class MapGeometry {
  MapGeometry({
    required this.width,
    required this.height,
    required this.coastline,
    required this.realms,
    required this.anchors,
  });

  final double width;
  final double height;
  final List<String> coastline;
  final Map<String, List<String>> realms;
  final Map<String, List<double>> anchors;

  /// Read the ground out of the vendored file.
  static Future<MapGeometry> load() async {
    final String text = await rootBundle.loadString('assets/map/geometry.json');
    final Map<String, Object?> parsed = jsonDecode(text) as Map<String, Object?>;
    final Map<String, List<String>> realms = <String, List<String>>{};
    final Map<String, Object?> realmMap =
        parsed['realms'] as Map<String, Object?>? ?? <String, Object?>{};
    realmMap.forEach((String key, Object? value) {
      realms[key] = (value as List<dynamic>).map((Object? path) => '$path').toList();
    });
    final Map<String, List<double>> anchors = <String, List<double>>{};
    final Map<String, Object?> anchorMap =
        parsed['anchors'] as Map<String, Object?>? ?? <String, Object?>{};
    anchorMap.forEach((String key, Object? value) {
      final List<dynamic> pair = value as List<dynamic>;
      anchors[key] = <double>[(pair[0] as num).toDouble(), (pair[1] as num).toDouble()];
    });
    return MapGeometry(
      width: (parsed['width'] as num?)?.toDouble() ?? 1000,
      height: (parsed['height'] as num?)?.toDouble() ?? 1200,
      coastline: (parsed['coastline'] as List<dynamic>? ?? <dynamic>[])
          .map((Object? path) => '$path')
          .toList(),
      realms: realms,
      anchors: anchors,
    );
  }
}

/// The picture of the map.
class RealmMapView extends StatelessWidget {
  const RealmMapView({
    super.key,
    required this.geometry,
    required this.states,
    required this.palette,
    required this.onRealmTap,
    this.selectedKey,
  });

  final MapGeometry geometry;
  final List<RealmState> states;
  final AppPalette palette;
  final ValueChanged<RealmState> onRealmTap;
  final String? selectedKey;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final double scale = math.min(
          constraints.maxWidth / geometry.width,
          constraints.maxHeight / (geometry.height + 64),
        );
        final double width = geometry.width * scale;
        final double height = (geometry.height + 64) * scale;
        return SizedBox(
          width: width,
          height: height,
          child: GestureDetector(
            onTapUp: (TapUpDetails details) {
              final double x = details.localPosition.dx / scale;
              final double y = details.localPosition.dy / scale;
              for (final RealmState state in states) {
                final List<double>? anchor = geometry.anchors[state.realm.key];
                if (anchor == null) continue;
                final double dx = anchor[0] - x;
                final double dy = anchor[1] - y;
                if (math.sqrt(dx * dx + dy * dy) < 26) {
                  onRealmTap(state);
                  return;
                }
              }
            },
            child: CustomPaint(
              painter: RealmMapPainter(
                geometry: geometry,
                states: states,
                palette: palette,
                scale: scale,
                selectedKey: selectedKey,
              ),
            ),
          ),
        );
      },
    );
  }
}

/// The painter of the map.
class RealmMapPainter extends CustomPainter {
  RealmMapPainter({
    required this.geometry,
    required this.states,
    required this.palette,
    required this.scale,
    this.selectedKey,
  });

  final MapGeometry geometry;
  final List<RealmState> states;
  final AppPalette palette;
  final double scale;
  final String? selectedKey;

  /// The colours of the four states of a realm.
  Color get _sea => palette.brightness == Brightness.dark
      ? const Color(0xFF0D1620)
      : const Color(0xFFDCE6EC);

  Color get _land => palette.brightness == Brightness.dark
      ? const Color(0xFF232A24)
      : const Color(0xFFEDE3C8);

  Color get _fog => palette.brightness == Brightness.dark
      ? const Color(0xFF2A3244)
      : const Color(0xFFCBD3E0);

  Color get _gilt => const Color(0xFFD4A72C);

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(scale);
    final double height = geometry.height + 64;

    canvas.drawRect(
      Rect.fromLTWH(0, 0, geometry.width, height),
      Paint()
        ..shader = RadialGradient(
          center: const Alignment(0, -0.12),
          radius: 0.85,
          colors: <Color>[
            _sea.withValues(alpha: 0.95),
            _sea.withValues(alpha: 0.6),
            _sea,
          ],
        ).createShader(Rect.fromLTWH(0, 0, geometry.width, height)),
    );

    for (final String path in geometry.coastline) {
      canvas.drawPath(
        _pathOf(path),
        Paint()
          ..color = _land
          ..style = PaintingStyle.fill,
      );
    }

    for (final RealmState state in states) {
      final List<String> paths = geometry.realms[state.realm.key] ?? <String>[];
      for (final String path in paths) {
        final Path shape = _pathOf(path);
        canvas.drawPath(shape, Paint()..color = _colourOf(state));
        canvas.drawPath(
          shape,
          Paint()
            ..color = _rimOf(state)
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.6,
        );
        if (state.state == 'fog') {
          canvas.save();
          canvas.clipPath(shape);
          canvas.drawRect(
            shape.bounds,
            Paint()
              ..color = _fog.withValues(alpha: 0.55)
              ..style = PaintingStyle.fill,
          );
          canvas.restore();
        }
      }
    }

    for (final RealmState state in states) {
      final List<double>? anchor = geometry.anchors[state.realm.key];
      if (anchor == null) continue;
      _paintCastles(canvas, state, anchor);
      _paintLabel(canvas, state, anchor);
    }

    _paintCampaignRoute(canvas);

    canvas.restore();
  }

  /// The gold road of the campaign, between the anchors of the claimed
  /// realms.
  void _paintCampaignRoute(Canvas canvas) {
    final List<RealmState> claimed = states
        .where((RealmState state) => state.state == 'claimed')
        .toList()
      ..sort((RealmState a, RealmState b) => a.assignedAt.compareTo(b.assignedAt));
    final List<Offset> points = <Offset>[];
    for (final RealmState state in claimed) {
      final List<double>? anchor = geometry.anchors[state.realm.key];
      if (anchor == null) continue;
      points.add(Offset(anchor[0], anchor[1]));
    }
    if (points.length < 2) return;
    final Path route = Path();
    route.moveTo(points.first.dx, points.first.dy);
    for (int i = 1; i < points.length; i++) {
      final Offset previous = points[i - 1];
      final Offset current = points[i];
      final Offset middle = Offset(
        (previous.dx + current.dx) / 2,
        (previous.dy + current.dy) / 2,
      );
      route.cubicTo(
        previous.dx + 6,
        previous.dy,
        middle.dx,
        middle.dy,
        current.dx,
        current.dy,
      );
    }
    canvas.drawPath(
      route,
      Paint()
        ..color = palette.floorThree
        ..style = PaintingStyle.stroke
        ..strokeWidth = 4
        ..strokeCap = StrokeCap.round,
    );
    canvas.drawPath(
      route,
      Paint()
        ..color = _gilt
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.2
        ..strokeCap = StrokeCap.round,
    );
    for (final Offset point in points) {
      canvas.drawCircle(
        point,
        4,
        Paint()..color = palette.floorThree,
      );
      canvas.drawCircle(
        point,
        3,
        Paint()..color = _gilt,
      );
    }
  }

  Color _colourOf(RealmState state) {
    switch (state.state) {
      case 'claimed':
        return _land.withValues(alpha: 0.95);
      case 'progress':
        return _land.withValues(alpha: 0.8);
      case 'hidden':
        return _fog.withValues(alpha: 0.35);
      default:
        return _land.withValues(alpha: 0.55);
    }
  }

  Color _rimOf(RealmState state) {
    switch (state.state) {
      case 'claimed':
        return _gilt;
      case 'progress':
        return _gilt.withValues(alpha: 0.6);
      case 'hidden':
        return palette.info.withValues(alpha: 0.7);
      default:
        return palette.border;
    }
  }

  /// The three castles of a realm, the lit ones first.
  void _paintCastles(Canvas canvas, RealmState state, List<double> anchor) {
    const List<List<double>> offsets = <List<double>>[
      <double>[-16, 4],
      <double>[0, 9],
      <double>[16, 4],
    ];
    for (int index = 0; index < offsets.length; index++) {
      final bool lit = index < state.castlesLit;
      final Offset centre = Offset(
        anchor[0] + offsets[index][0],
        anchor[1] + offsets[index][1],
      );
      canvas.save();
      canvas.translate(centre.dx, centre.dy);
      final Path castle = Path()
        ..moveTo(-7, 9)
        ..lineTo(-7, -1)
        ..lineTo(-5, -1)
        ..lineTo(-5, -6)
        ..lineTo(-2, -6)
        ..lineTo(-2, -1)
        ..lineTo(2, -1)
        ..lineTo(2, -6)
        ..lineTo(5, -6)
        ..lineTo(5, -1)
        ..lineTo(7, -1)
        ..lineTo(7, 9)
        ..close();
      canvas.drawPath(
        castle,
        Paint()
          ..color = lit ? _gilt : palette.border
          ..style = PaintingStyle.fill,
      );
      canvas.drawPath(
        castle,
        Paint()
          ..color = palette.ink.withValues(alpha: lit ? 0.7 : 0.3)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 0.8,
      );
      canvas.restore();
    }
  }

  /// The name of a realm, under its castles.
  void _paintLabel(Canvas canvas, RealmState state, List<double> anchor) {
    final TextPainter painter = TextPainter(
      text: TextSpan(
        text: state.realm.nameFa,
        style: TextStyle(
          color: state.state == 'fog'
              ? palette.muted
              : palette.ink.withValues(alpha: 0.9),
          fontSize: 15,
          fontWeight: FontWeight.w600,
        ),
      ),
      textDirection: TextDirection.rtl,
      textAlign: TextAlign.center,
    )..layout();
    painter.paint(
      canvas,
      Offset(anchor[0] - painter.width / 2, anchor[1] + 30),
    );
  }

  /// Read a path of the ground.
  ///
  /// The ground is a series of straight lines: ``M``, ``L`` and ``Z``. The
  /// parser walks the tokens and emits the same shape as the painter of
  /// the web app, so the geometry is drawn exactly as it was written.
  Path _pathOf(String data) {
    final Path path = Path();
    final RegExp tokenPattern = RegExp(r'([A-Za-z])|(-?\d+(?:\.\d+)?)');
    final List<RegExpMatch> matches = tokenPattern.allMatches(data).toList();
    int index = 0;
    String command = 'M';
    while (index < matches.length) {
      final RegExpMatch match = matches[index];
      final String token = match.group(0)!;
      if (token.length == 1 && RegExp(r'[A-Za-z]').hasMatch(token)) {
        command = token.toUpperCase();
        index++;
        continue;
      }
      final double x = double.parse(token);
      final double y = index + 1 < matches.length
          ? double.parse(matches[index + 1].group(0)!)
          : 0;
      if (command == 'M') {
        path.moveTo(x, y);
        command = 'L';
      } else if (command == 'L') {
        path.lineTo(x, y);
      } else if (command == 'Z') {
        path.close();
        command = 'M';
      }
      index += 2;
    }
    return path;
  }

  @override
  bool shouldRepaint(covariant RealmMapPainter oldDelegate) =>
      oldDelegate.states != states || oldDelegate.palette != palette;
}
