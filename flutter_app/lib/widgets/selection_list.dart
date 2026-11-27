/// The selection of a list: one component for every list of the app.
///
/// A list of things the user can act upon shows the same bar at the top
/// when something is picked: how many things are picked, and the actions.
/// The action that throws things away asks before it does.
library;

import 'package:flutter/material.dart';

/// A list whose items can be picked, and acted upon together.
class SelectionList<T> extends StatefulWidget {
  const SelectionList({
    super.key,
    required this.items,
    required this.itemBuilder,
    required this.onDelete,
    this.itemKey,
    this.actions = const <Widget>[],
    this.selectionHint = 'انتخاب‌شده',
    this.empty,
  });

  /// The items of the list.
  final List<T> items;

  /// The key of an item, so the selection survives the reordering.
  final Key Function(T item)? itemKey;

  /// The building of an item.
  final Widget Function(
    BuildContext context,
    T item,
    bool selected,
    VoidCallback onTap,
  ) itemBuilder;

  /// The action that throws the picked items away.
  final Future<void> Function(List<T> items) onDelete;

  /// The other actions of the bar.
  final List<Widget> actions;

  /// The word that names the picked items.
  final String selectionHint;

  /// What the list shows when it is empty.
  final Widget? empty;

  @override
  State<SelectionList<T>> createState() => _SelectionListState<T>();
}

class _SelectionListState<T> extends State<SelectionList<T>> {
  final Set<Key> _selected = <Key>{};

  bool get _picking => _selected.isNotEmpty;

  void _toggle(Key key) {
    setState(() {
      if (!_selected.remove(key)) _selected.add(key);
    });
  }

  /// The picked items, in the order of the list.
  List<T> get _picked => widget.items
      .where(
        (T item) => _selected.contains(widget.itemKey?.call(item) ?? ValueKey<T>(item)),
      )
      .toList();

  Future<void> _delete() async {
    final List<T> items = _picked;
    if (items.isEmpty) return;
    final bool? sure = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) => AlertDialog(
        title: const Text('حذف'),
        content: Text('${items.length} مورد انتخاب شده. حذف شوند؟'),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('نه'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('آری'),
          ),
        ],
      ),
    );
    if (sure != true) return;
    await widget.onDelete(items);
    if (!mounted) return;
    setState(_selected.clear);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        if (_picking)
          Material(
            color: Theme.of(context).colorScheme.secondaryContainer,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              child: Row(
                children: <Widget>[
                  Text('${_selected.length} ${widget.selectionHint}'),
                  const Spacer(),
                  ...widget.actions,
                  IconButton(
                    tooltip: 'حذف',
                    onPressed: _delete,
                    icon: const Icon(Icons.delete_outline),
                  ),
                  IconButton(
                    tooltip: 'برداشتن انتخاب',
                    onPressed: () => setState(_selected.clear),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
            ),
          ),
        Expanded(
          child: widget.items.isEmpty
              ? (widget.empty ?? const SizedBox.shrink())
              : ListView.builder(
                  itemCount: widget.items.length,
                  itemBuilder: (BuildContext context, int index) {
                    final T item = widget.items[index];
                    final Key key = widget.itemKey?.call(item) ?? ValueKey<T>(item);
                    return widget.itemBuilder(
                      context,
                      item,
                      _selected.contains(key),
                      () => _toggle(key),
                    );
                  },
                ),
        ),
      ],
    );
  }
}
