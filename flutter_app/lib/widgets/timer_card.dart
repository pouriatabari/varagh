/// The timer of the user: the block that is running, and the ones that
/// were finished.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sqflite/sqflite.dart';

import '../data/time_entries.dart';
import '../i18n.dart';

/// The card that runs the timer on the dashboard.
class TimerCard extends StatefulWidget {
  const TimerCard({super.key, required this.database});

  final Database database;

  @override
  State<TimerCard> createState() => _TimerCardState();
}

class _TimerCardState extends State<TimerCard> {
  late final TimeRepository _time;
  TimeEntry? _running;
  List<TimeEntry> _today = <TimeEntry>[];
  String _kind = 'work';
  Timer? _ticker;

  @override
  void initState() {
    super.initState();
    _time = TimeRepository(widget.database);
    _load();
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (_running != null) setState(() {});
    });
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    final List<TimeEntry> today = await _time.listOfDay(DateTime.now());
    TimeEntry? running;
    for (final TimeEntry entry in today) {
      if (entry.endedAt == null) {
        running = entry;
        break;
      }
    }
    if (!mounted) return;
    setState(() {
      _today = today;
      _running = running;
    });
  }

  Future<void> _start() async {
    await _time.start(kind: _kind);
    await _load();
  }

  Future<void> _stop() async {
    if (_running == null) return;
    await _time.stop(_running!.id);
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(Fa.t('nav.tasks'), style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Row(
              children: <Widget>[
                Text(
                  _display(),
                  style: TextStyle(
                    fontSize: 36,
                    fontWeight: FontWeight.w600,
                    color: _running == null ? Theme.of(context).hintColor : null,
                    fontFeatures: const <FontFeature>[FontFeature.tabularFigures()],
                  ),
                ),
                const Spacer(),
                if (_running == null) ...<Widget>[
                  DropdownButton<String>(
                    value: _kind,
                    items: const <DropdownMenuItem<String>>[
                      DropdownMenuItem<String>(value: 'work', child: Text('کار')),
                      DropdownMenuItem<String>(value: 'study', child: Text('مطالعه')),
                      DropdownMenuItem<String>(value: 'learning', child: Text('یادگیری')),
                      DropdownMenuItem<String>(value: 'overtime', child: Text('اضافه‌کار')),
                    ],
                    onChanged: (String? value) {
                      if (value != null) setState(() => _kind = value);
                    },
                  ),
                  const SizedBox(width: 8),
                  FilledButton(onPressed: _start, child: const Text('آغاز')),
                ] else
                  OutlinedButton(onPressed: _stop, child: const Text('پایان')),
              ],
            ),
            const SizedBox(height: 8),
            for (final TimeEntry entry in _today)
              ListTile(
                dense: true,
                title: Text(entry.kind),
                subtitle: Text(_hhmm(entry.startedAt)),
                trailing: Text('${entry.durationMinutes ?? 0} دقیقه'),
              ),
          ],
        ),
      ),
    );
  }

  String _display() {
    if (_running == null) return '۰۰:۰۰:۰۰';
    final Duration elapsed = DateTime.now().difference(_running!.startedAt);
    final String hours = elapsed.inHours.toString().padLeft(2, '0');
    final String minutes = (elapsed.inMinutes % 60).toString().padLeft(2, '0');
    final String seconds = (elapsed.inSeconds % 60).toString().padLeft(2, '0');
    return '$hours:$minutes:$seconds';
  }

  String _hhmm(DateTime when) {
    final String h = when.hour.toString().padLeft(2, '0');
    final String m = when.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }
}
