(function () {
  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  function getType() {
    const el = qs('#id_question_type');
    return el ? (el.value || '').trim() : '';
  }

  function toggleUI() {
    const type = getType();

    // Inline group (Choice inline). Django default: #choice_set-group yoki model nomiga qarab.
    // Ikkalasini ham tekshiramiz:
    const inlineGroup =
      qs('#choice_set-group') ||
      qs('#choice-group') ||
      qs('[id$="-choice_set-group"]') ||
      qs('[id$="-choice-group"]');

    // correct_answer field row
    const correctRow = qs('.form-row.field-correct_answer') || qs('.field-correct_answer');

    const needsChoices = (type === 'single' || type === 'multiple' || type === 'true_false');
    const needsCorrectAnswer = (type === 'short' || type === 'numeric' || type === 'essay');

    if (inlineGroup) inlineGroup.style.display = needsChoices ? '' : 'none';
    if (correctRow) correctRow.style.display = needsCorrectAnswer ? '' : 'none';

    // radio behavior: single/true_false
    if (needsChoices && (type === 'single' || type === 'true_false')) {
      const checks = qsa('input[type="checkbox"][name$="-is_correct"]');
      checks.forEach(ch => {
        ch.addEventListener('change', () => {
          if (!ch.checked) return;
          checks.forEach(other => { if (other !== ch) other.checked = false; });
        });
      });
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    const typeSelect = qs('#id_question_type');
    if (typeSelect) {
      typeSelect.addEventListener('change', toggleUI);
    }
    toggleUI();
  });
})();
