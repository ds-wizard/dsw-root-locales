import collections
import dataclasses
import json
import pathlib
import uuid

from babel.messages.catalog import Catalog
from babel.messages.pofile import write_po

import dsw.models.knowledge_model.flat as km_flat

ROOT = pathlib.Path(__file__).parent


@dataclasses.dataclass
class ExtractedMessage:
    msgid: str
    entity_type: str
    entity_uuid: uuid.UUID
    entity_attribute: str

    @property
    def path(self) -> str:
        return f'{self.entity_type}:{self.entity_uuid}:{self.entity_attribute}'

    @property
    def line(self) -> int:
        return 0


class MessageExtractor:

    def __init__(self, km: km_flat.KnowledgeModel):
        self.km = km
        self.messages = []

    def reset(self):
        self.messages.clear()

    def _extract_messages_answer(self, answer: km_flat.Answer):
        self.messages.append(ExtractedMessage(
            msgid=answer.label,
            entity_type='answer',
            entity_uuid=answer.uuid,
            entity_attribute='label',
        ))
        if answer.advice:
            self.messages.append(ExtractedMessage(
                msgid=answer.advice,
                entity_type='answer',
                entity_uuid=answer.uuid,
                entity_attribute='advice',
            ))

        for question_uuid in answer.follow_up_uuids:
            question = self.km.entities.questions.get(question_uuid)
            self._extract_messages_question(question)

    def _extract_messages_choice(self, choice: km_flat.Choice):
        self.messages.append(ExtractedMessage(
            msgid=choice.label,
            entity_type='choice',
            entity_uuid=choice.uuid,
            entity_attribute='label',
        ))

    def _extract_messages_question(self, question: km_flat.Question):
        self.messages.append(ExtractedMessage(
            msgid=question.title,
            entity_type='question',
            entity_uuid=question.uuid,
            entity_attribute='title',
        ))
        if question.text:
            self.messages.append(ExtractedMessage(
                msgid=question.text,
                entity_type='question',
                entity_uuid=question.uuid,
                entity_attribute='text',
            ))

        if isinstance(question, km_flat.ListQuestion):
            for question_uuid in question.item_template_question_uuids:
                item_question = self.km.entities.questions.get(question_uuid)
                self._extract_messages_question(item_question)
        if isinstance(question, km_flat.MultiChoiceQuestion):
            for choice_uuid in question.choice_uuids:
                choice = self.km.entities.choices.get(choice_uuid)
                self._extract_messages_choice(choice)
        if isinstance(question, km_flat.OptionsQuestion):
            for answer_uuid in question.answer_uuids:
                answer = self.km.entities.answers.get(answer_uuid)
                self._extract_messages_answer(answer)

        for reference_uuid in question.reference_uuids:
            reference = self.km.entities.references.get(reference_uuid)
            self._extract_messages_reference(reference)

    def _extract_messages_reference(self, reference: km_flat.Reference):
        if isinstance(reference, km_flat.URLReference):
            self.messages.append(ExtractedMessage(
                msgid=reference.label,
                entity_type='url-reference',
                entity_uuid=reference.uuid,
                entity_attribute='label',
            ))
        if isinstance(reference, km_flat.CrossReference):
            self.messages.append(ExtractedMessage(
                msgid=reference.description,
                entity_type='cross-reference',
                entity_uuid=reference.uuid,
                entity_attribute='description',
            ))

    def _extract_messages_chapter(self, chapter: km_flat.Chapter):
        self.messages.append(ExtractedMessage(
            msgid=chapter.title,
            entity_type='chapter',
            entity_uuid=chapter.uuid,
            entity_attribute='title',
        ))
        if chapter.text:
            self.messages.append(ExtractedMessage(
                msgid=chapter.text,
                entity_type='chapter',
                entity_uuid=chapter.uuid,
                entity_attribute='text',
            ))
        for question_uuid in chapter.question_uuids:
            question = self.km.entities.questions.get(question_uuid)
            self._extract_messages_question(question)

    def _extract_messages_phase(self, phase: km_flat.Phase):
        self.messages.append(ExtractedMessage(
            msgid=phase.title,
            entity_type='phase',
            entity_uuid=phase.uuid,
            entity_attribute='title',
        ))
        if phase.description:
            self.messages.append(ExtractedMessage(
                msgid=phase.description,
                entity_type='phase',
                entity_uuid=phase.uuid,
                entity_attribute='description',
            ))

    def _extract_messages_tag(self, tag: km_flat.Tag):
        self.messages.append(ExtractedMessage(
            msgid=tag.name,
            entity_type='tag',
            entity_uuid=tag.uuid,
            entity_attribute='name',
        ))
        if tag.description:
            self.messages.append(ExtractedMessage(
                msgid=tag.description,
                entity_type='tag',
                entity_uuid=tag.uuid,
                entity_attribute='description',
            ))

    def _extract_messages_metric(self, metric: km_flat.Metric):
        self.messages.append(ExtractedMessage(
            msgid=metric.title,
            entity_type='metrics',
            entity_uuid=metric.uuid,
            entity_attribute='title',
        ))
        if metric.description:
            self.messages.append(ExtractedMessage(
                msgid=metric.description,
                entity_type='metrics',
                entity_uuid=metric.uuid,
                entity_attribute='description',
            ))

    def _extract_messages_resource_collection(self, rc: km_flat.ResourceCollection):
        self.messages.append(ExtractedMessage(
            msgid=rc.title,
            entity_type='resource_collection',
            entity_uuid=rc.uuid,
            entity_attribute='title',
        ))

        for rp_uuid in rc.resource_page_uuids:
            rp = self.km.entities.resource_pages.get(rp_uuid)
            self._extract_messages_resource_page(rp)

    def _extract_messages_resource_page(self, rp: km_flat.ResourcePage):
        self.messages.append(ExtractedMessage(
            msgid=rp.title,
            entity_type='resource_page',
            entity_uuid=rp.uuid,
            entity_attribute='title',
        ))
        if rp.content:
            self.messages.append(ExtractedMessage(
                msgid=rp.content,
                entity_type='resource_page',
                entity_uuid=rp.uuid,
                entity_attribute='content',
            ))

    def extract_messages(self) -> list[ExtractedMessage]:
        self.reset()
        for chapter_uuid in self.km.chapter_uuids:
            chapter = self.km.entities.chapters.get(chapter_uuid)
            self._extract_messages_chapter(chapter)
        return self.messages


def build_pot(
    messages: list[ExtractedMessage],
    out_path: str | pathlib.Path,
) -> None:
    catalog = Catalog(
        project='Common DSW Knowledge Model',
        version='2.7.0',
        charset='utf-8',
    )
    # 1) Group locations by msgid
    locs_by_msgid: dict[str, set[tuple[str, int]]] = collections.defaultdict(set)
    for occ in messages:
        if not occ.msgid:
            continue
        locs_by_msgid[occ.msgid].add((occ.path, int(occ.line)))

    for msgid, locs in sorted(locs_by_msgid.items(), key=lambda kv: kv[0]):
        # Sort locations for stable output (nice diffs)
        locations = sorted(locs, key=lambda t: (t[0], t[1]))

        catalog.add(
            msgid,
            locations=locations,
            # IMPORTANT: do not set `context=` if you want one entry per msgid
        )

    # 3) Write .pot
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as f:
        write_po(
            f,
            catalog,
            sort_output=True,
            width=-1,
        )


if __name__ == '__main__':
    input_file = ROOT / 'km.json'
    output_file = ROOT / 'messages.pot'
    data = json.loads(input_file.read_text(encoding='utf-8'))
    km = km_flat.KnowledgeModel.model_validate(data)
    messages = MessageExtractor(km).extract_messages()
    build_pot(messages, output_file)
