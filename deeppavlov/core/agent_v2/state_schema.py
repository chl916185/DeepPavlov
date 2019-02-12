from datetime import datetime
import uuid
import json
from json import JSONEncoder

from mongoengine import Document, DynamicDocument, ReferenceField, ListField, StringField, DynamicField, \
    UUIDField, DateTimeField, FloatField, DictField

from mongoengine import connect

db = connect(host='localhost', port=27017)


class User(Document):
    # user_id = UUIDField(required=True) #
    user_telegram_id = UUIDField(required=True, unique=True)
    user_type = StringField(required=True, choices=['human', 'bot'], default='human')
    device_type = DynamicField()
    personality = DynamicField()

    def to_dict(self):
        return {'id': str(self.id),
                'user_telegram_id': str(self.user_telegram_id),
                'user_type': self.user_type,
                'device_type': self.device_type,
                'personality': self.personality}


class Utterance(Document):
    # utt_id = UUIDField(required=True) # managed by db
    text = StringField(required=True)
    annotations = DictField(default={'ner': {}, 'coref': {}, 'sentiment': {}})
    user = ReferenceField(User, required=True)
    date = DateTimeField(required=True)

    meta = {'allow_inheritance': True}

    def to_dict(self):
        return {'id': str(self.id),
                'text': self.text,
                'user_id': str(self.user.id),
                'annotations': self.annotations,
                'date': str(self.date)}


class DialogHistory(DynamicDocument):
    utterances = ListField(ReferenceField(Utterance), required=True)

    def to_dict(self):
        return {'utterances': [utt.to_dict() for utt in self.utterances]}


# class Annotations(Document):
#     annotations = DictField(required=True)
#     utterance = ReferenceField(Utterance, required=True)
#
#     def to_dict(self):
#         return {'id': self.id,
#                 'annotations': self.annotations,
#                 'utterance': self.utterance.to_dict()}


class BotUtterance(Utterance):
    active_skill = StringField()
    confidence = FloatField()

    def to_dict(self):
        return {
            'id': str(self.id),
            'active_skill': self.active_skill,
            'confidence': self.confidence,
            'text': self.text,
            'user_id': str(self.user.id),
            'annotations': self.annotations,
            'date': str(self.date)
        }


class Dialog(DynamicDocument):
    # dialog_id = UUIDField(required=True) #managed by db
    location = DynamicField()
    history = ReferenceField(DialogHistory, required=True)
    users = ListField(ReferenceField(User), required=True)
    channel_type = StringField(choices=['telegram', 'vkontakte', 'facebook'], default='telegram')

    def to_dict(self):
        return {
            'id': str(self.id),
            'location': self.location,
            'history': self.history.to_dict(),
            'user': [u.to_dict() for u in self.users if u.user_type == 'human'][0],
            'bot': [u.to_dict() for u in self.users if u.user_type == 'bot'][0],
            'channel_type': self.channel_type
        }


class MongoEncoder(JSONEncoder):
    def default(self, obj):
        if issubclass(obj, Document):
            return obj.to_dict()
        return JSONEncoder.default(self, obj)

    # def __dict__(self):
    #     # return "%s %s %s %s" % (self.location, self.date, self.history, self.users)
    #     return {'location': self.location,
    #             'date': self.date,
    #             'history': self.history,
    #             'users': self.users}

    # def save(self, force_insert=False, validate=True, clean=True,
    #          write_concern=None, cascade=None, cascade_kwargs=None,
    #          _refs=None, save_condition=None, signal_kwargs=None, **kwargs):
    #     self.history.save()
    #     super().save()


# d = Dialog()
# string_of_user = "Hi"
# u = Utterance(text=string_of_user, annotations=[])
# u.save()
# Utterance.objects.filter(users=some_user)
# User.id

Dialog.objects.delete()
Utterance.objects.delete()
BotUtterance.objects.delete()
DialogHistory.objects.delete()
User.objects.delete()

########################### Test case #######################################

default_anno = {"ner": [], "coref": [], "sentiment": []}
h_user = User(user_telegram_id=uuid.uuid4())
b_user = User(user_telegram_id=uuid.uuid4(), user_type='bot')

h_utt_1 = Utterance(text='Привет!', user=h_user, annotations=default_anno, date=datetime.utcnow())
b_utt_1 = BotUtterance(text='Привет, я бот!', user=b_user, annotations=default_anno, active_skill='chitchat',
                       confidence=0.85, date=datetime.utcnow())
# h_anno_1 = Annotations(default_anno, utterance=h_utt_1)
# b_anno_1 = Annotations(default_anno, utterance=b_utt_1)

h_utt_2 = Utterance(text='Как дела?', user=h_user, annotations=default_anno,
                    date=datetime.utcnow())
b_utt_2 = BotUtterance(text='Хорошо, а у тебя как?', user=b_user, annotations=default_anno,
                       active_skill='chitchat',
                       confidence=0.9333, date=datetime.utcnow())
# h_anno_2 = Annotations(default_anno, utterance=h_utt_2)
# b_anno_2 = Annotations(default_anno, utterance=b_utt_2)

h_utt_3 = Utterance(text='И у меня нормально. Когда родился Петр Первый?', user=h_user, annotations=default_anno,
                    date=datetime.utcnow())
b_utt_3 = BotUtterance(text='в 1672 году', user=b_user, annotations=default_anno, active_skill='odqa', confidence=0.74,
                       date=datetime.utcnow())
# h_anno_3 = Annotations(default_anno, utterance=h_utt_3)
# b_anno_3 = Annotations(default_anno, utterance=b_utt_3)

h_utt_4 = Utterance(text='спасибо', user=h_user, annotations=default_anno, date=datetime.utcnow())

dh = DialogHistory([h_utt_1, b_utt_1, h_utt_2, b_utt_2, h_utt_3, b_utt_3, h_utt_4])
d = Dialog(history=dh, users=[h_user, b_user], channel_type='telegram')

h_user.save()
b_user.save()

h_utt_1.save()
b_utt_1.save()

h_utt_2.save()
b_utt_2.save()

h_utt_3.save()
b_utt_3.save()

h_utt_4.save()

dh.save()
d.save()

h_utt_5 = Utterance(text='Когда началась Вторая Мировая?', user=h_user, annotations=default_anno,
                    date=datetime.utcnow())
b_utt_5 = BotUtterance(text='1939', user=b_user, annotations=default_anno, active_skill='odqa', confidence=0.99,
                       date=datetime.utcnow())
h_utt_6 = Utterance(text='Спасибо, бот!', user=h_user, annotations=default_anno, date=datetime.utcnow())
dh_1 = DialogHistory([h_utt_5, b_utt_5, h_utt_6])
d_1 = Dialog(history=dh_1, users=[h_user, b_user], channel_type='facebook')
h_utt_5.save()
b_utt_5.save()
h_utt_6.save()
dh_1.save()
d_1.save()

count = 0
total = {'version': 0.9}

batch = []
for d in Dialog.objects:
    if count < 2:
        info = d.to_dict()
        batch.append(info)
        count += 1

total.update({'batch': batch})
print(total)