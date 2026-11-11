"""Campaign failures halt a shared budget without erasing prior spend."""
from decimal import Decimal
import unittest

from cost_accounting import CostBudget, BudgetRejected


class CampaignBudgetSeamTests(unittest.TestCase):
    def test_terminal_error_halts_next_model_and_preserves_spend(self):
        budget=CostBudget(Decimal('10'),192,approval_id='fictional-offline')
        ticket=budget.reserve(Decimal('1'))
        budget.settle(ticket,Decimal('0.25'))
        budget.halt('audit_persistence_failed')
        self.assertEqual(budget.to_dict()['spent_usd'],'0.25')
        with self.assertRaisesRegex(BudgetRejected,'audit_persistence_failed'):
            budget.reserve(Decimal('0.01'))

    def test_halt_preserves_original_unknown_usage_reason(self):
        budget=CostBudget(Decimal('10'),192,approval_id='fictional-offline')
        ticket=budget.reserve(Decimal('1'))
        budget.settle(ticket,None)
        budget.halt('campaign_interrupted')
        self.assertEqual(budget.to_dict()['halt_reason'],'actual_cost_unconfirmed')

    def test_halt_reason_is_bounded_fixed_code(self):
        budget=CostBudget(Decimal('10'),192,approval_id='fictional-offline')
        with self.assertRaises(ValueError):
            budget.halt('unsafe reason containing arbitrary text')
