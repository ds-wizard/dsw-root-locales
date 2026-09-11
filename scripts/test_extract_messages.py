"""Regression checks for source messages outside the chapter/question tree."""

import importlib.util
import pathlib
import sys
import tempfile
import unittest
import uuid
from types import SimpleNamespace

from babel.messages.pofile import read_po

SCRIPT = pathlib.Path(__file__).with_name('extract-messages.py')
SPEC = importlib.util.spec_from_file_location('extract_messages', SCRIPT)
extract = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = extract
SPEC.loader.exec_module(extract)


def entity(**fields):
    return SimpleNamespace(uuid=uuid.uuid4(), **fields)


class ExtractMessagesTest(unittest.TestCase):
    def setUp(self):
        self.chapter = entity(title='Chapter', text=None, question_uuids=[])
        self.metric = entity(title='Metric', abbreviation='M', description='Metric description')
        self.phase = entity(title='Phase', description='Phase description')
        self.tag = entity(name='Tag', description='Tag description')
        self.page = entity(title='Page', content='Page content')
        self.collection = entity(title='Collection', resource_page_uuids=[self.page.uuid])
        entities = SimpleNamespace(
            chapters={self.chapter.uuid: self.chapter},
            metrics={self.metric.uuid: self.metric},
            phases={self.phase.uuid: self.phase},
            tags={self.tag.uuid: self.tag},
            resource_collections={self.collection.uuid: self.collection},
            resource_pages={self.page.uuid: self.page},
        )
        self.km = SimpleNamespace(
            entities=entities,
            chapter_uuids=[self.chapter.uuid],
            metric_uuids=[self.metric.uuid],
            phase_uuids=[self.phase.uuid],
            tag_uuids=[self.tag.uuid],
            resource_collection_uuids=[self.collection.uuid],
        )

    def test_extracts_all_reachable_top_level_entities(self):
        messages = extract.MessageExtractor(self.km).extract_messages()
        self.assertEqual({message.msgid for message in messages}, {
            'Chapter', 'Metric', 'M', 'Metric description', 'Phase', 'Phase description',
            'Tag', 'Tag description', 'Collection', 'Page', 'Page content',
        })
        self.assertIn(
            f'metric:{self.metric.uuid}:abbreviation',
            {message.path for message in messages},
        )
        self.assertIn(
            f'resourcePage:{self.page.uuid}:content',
            {message.path for message in messages},
        )

    def test_ignores_unreferenced_entities(self):
        orphan = entity(title='Unreferenced', description=None)
        self.km.entities.phases[orphan.uuid] = orphan
        messages = extract.MessageExtractor(self.km).extract_messages()
        self.assertNotIn('Unreferenced', {message.msgid for message in messages})

    def test_optional_fields_and_repeated_extraction(self):
        self.metric.abbreviation = None
        self.metric.description = None
        self.phase.description = None
        self.tag.description = None
        extractor = extract.MessageExtractor(self.km)
        first = list(extractor.extract_messages())
        self.assertEqual(first, extractor.extract_messages())
        self.assertEqual(len(first), 7)

    def test_pot_groups_shared_messages_and_skips_whitespace(self):
        self.phase.title = self.chapter.title
        self.tag.description = ' \n '
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / 'messages.pot'
            extract.build_pot(extract.MessageExtractor(self.km).extract_messages(), path)
            text = path.read_text(encoding='utf-8')
            with path.open(encoding='utf-8') as handle:
                catalog = read_po(handle, abort_invalid=True)
        self.assertIn(f'chapter:{self.chapter.uuid}:title', text)
        self.assertIn(f'phase:{self.phase.uuid}:title', text)
        self.assertEqual(sum(message.id == 'Chapter' for message in catalog), 1)
        self.assertIsNone(catalog.get(' \n '))
        self.assertTrue(all(not message.string for message in catalog if message.id))


if __name__ == '__main__':
    unittest.main()
