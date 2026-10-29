#!/usr/bin/env python3
"""Mutation tests ensuring the byte comparator cannot hide code/padding changes."""
import hashlib
import json
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
import deep_section_analysis
import analyze
import verify_evidence
from capture import b58
from compare import compare
class ComparisonTests(unittest.TestCase):
    def test_equal(self): self.assertTrue(compare(b'abc\0\0',b'abc\0\0')['full_byte_equality'])
    def test_code_mutation(self): self.assertEqual(compare(b'abc\0\0',b'axc\0\0')['first_difference'],1)
    def test_padding_mutation(self): self.assertEqual(compare(b'abc\0\0',b'abc\0x')['first_difference'],4)
    def test_truncated_padding(self): self.assertFalse(compare(b'abc\0\0',b'abc\0')['full_byte_equality'])
    def test_extended_padding(self): self.assertFalse(compare(b'abc\0',b'abc\0\0')['full_byte_equality'])
    def test_empty(self): self.assertEqual(compare(b'a',b'')['first_difference'],0)


class RelocationTargetTests(unittest.TestCase):
    def test_target_section_uses_address_not_file_offset(self):
        blob = bytearray(64)
        struct.pack_into('<QQ', blob, 0, 0x1000, 2)
        elf = SimpleNamespace(
            b=bytes(blob),
            symbols={},
            lo=0x2000,
            hi=0x3000,
            secs={
                '.rel.dyn': (0, 9, 0, 0, 0, 16, 0, 0, 1, 16),
                '.rodata': (0, 1, 2, 0x1000, 0x20, 0x100, 0, 0, 1, 0),
            },
        )
        report = deep_section_analysis.analyze_relocations(elf)
        self.assertEqual(report['entries'][0]['target_section'], '.rodata')


class InstructionLogNameTests(unittest.TestCase):
    def names(self, name):
        blob = (analyze.ROOT / 'evidence/original' / name / 'deployed.so').read_bytes()
        return set(analyze.instruction_log_names(blob, analyze.known_instruction_names(name)))

    def test_idl_names_do_not_absorb_adjacent_text(self):
        pump = self.names('pump')
        self.assertIn('Buy', pump)
        self.assertIn('UpdateBuybackConfig', pump)
        self.assertIn('IdlResizeAccount', pump)
        self.assertNotIn('BuyCreateV2Disabled', pump)
        self.assertNotIn('UpdateBuybackConfigAn', pump)
        self.assertNotIn('IdlResizeAccountdata', pump)

        amm = self.names('pump_amm')
        self.assertIn('ClaimCashback', amm)
        self.assertIn('IdlCreateAccount', amm)
        self.assertNotIn('ClaimCashbacksol', amm)
        self.assertNotIn('IdlCreateAccountanchor', amm)

        fees = self.names('pump_fees')
        self.assertIn('Withdraw', fees)
        self.assertIn('CrankDonationFeePda', fees)
        self.assertNotIn('Withdrawaccountsol', fees)
        self.assertNotIn('CrankDonationFeePdaFee', fees)

    def test_program_names_fall_back_to_captures(self):
        self.assertEqual(
            analyze.program_names(),
            ['pump', 'pump_amm', 'pump_fees', 'mayhem'],
        )

    def test_mayhem_fallback_is_unchanged(self):
        names = self.names('mayhem')
        self.assertEqual(len(names), 25)
        self.assertIn('Buy', names)
        self.assertIn('InitializeGlobalParams', names)


class ProgramDataAuthorityTagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        workspace = tempfile.TemporaryDirectory()
        cls.addClassCleanup(workspace.cleanup)
        cls.root = pathlib.Path(workspace.name)
        (cls.root / 'scripts').mkdir()
        for name in ('verify_evidence.py', 'capture.py', 'analyze.py'):
            shutil.copyfile(analyze.ROOT / 'scripts' / name, cls.root / 'scripts' / name)
        shutil.copytree(analyze.ROOT / 'evidence/upstream', cls.root / 'evidence/upstream')
        for relative in verify_evidence.EXPECTED_CAPTURES:
            shutil.copytree(analyze.ROOT / relative, cls.root / relative)
        cls.folder = cls.root / 'evidence/original/pump_fees'
        cls.original_data = (cls.folder / 'programdata-account.bin').read_bytes()
        cls.original_record = json.loads((cls.folder / 'capture.json').read_text())

    def verify_tag(self, tag, optimized):
        data = bytearray(self.original_data)
        data[12] = tag
        record = dict(self.original_record)
        # Keep hashes and declared authority consistent so the tag itself is tested.
        record['programdata_sha256'] = hashlib.sha256(data).hexdigest()
        record['upgrade_authority'] = b58(data[13:45]) if tag else None
        (self.folder / 'programdata-account.bin').write_bytes(data)
        (self.folder / 'capture.json').write_text(json.dumps(record))
        command = [sys.executable, *(['-O'] if optimized else []), 'scripts/verify_evidence.py']
        return subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=30)

    def test_valid_authority_option_tags(self):
        for tag in (0, 1):
            for optimized in (False, True):
                with self.subTest(tag=tag, optimized=optimized):
                    result = self.verify_tag(tag, optimized)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('9 captures verified', result.stdout)

    def test_invalid_authority_option_tags(self):
        for tag in (2, 255):
            for optimized in (False, True):
                with self.subTest(tag=tag, optimized=optimized):
                    result = self.verify_tag(tag, optimized)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertIn('invalid ProgramData upgrade authority option tag', result.stderr)
                    self.assertIn('evidence/original/pump_fees', result.stderr)


if __name__=='__main__': unittest.main()
