# xmpp protocol IM relay class

import os, sys
import json, re
import logging
from collections import defaultdict

from PyQt5.QtCore import *

import sleekxmpp

from .unimessage import XmppMessage


class QSleek(QThread):
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    newMessage = pyqtSignal('QString')   # just the message
    peerConnected = pyqtSignal('QString')   # peer identifier
    peerDisconnected = pyqtSignal('QString')  # peer identifier
    peerEnterGroup = pyqtSignal('QString')  # group identifier
    newGroupMessage = pyqtSignal('QString', 'QString')  # group identifier, msg

    def __init__(self, parent=None):
        super(QSleek, self).__init__(parent)

        self.unimsgcls = XmppMessage
        self.src_pname = ''

        self.self_user = ''
        self.peer_user = ''
        self.nick_name = ''

        self.xmpp = None  # ClientXMPP()

        self.initXmpp()
        return

    # abstract method implemention
    # @return True|False
    def sendMessage(self, msg, peer):
        rc = self.xmpp.send_message(mto=peer, mbody=msg)
        qDebug(str(rc))
        return True

    # @return True|False
    def sendGroupMessage(self, msg, peer):
        rc = self.muc_send_message(peer, msg)
        qDebug(str(rc))
        return rc

    # @return True|False
    def sendFileMessage(self, msg, peer):
        return

    # @return True|False
    def sendVoiceMessage(self, msg, peer):
        return

    # @return True|False
    def sendImageMessage(self, msg, peer):
        return

    def disconnectIt(self):
        self.xmpp.disconnect()
        return

    def isConnected(self):
        # st = self.xmpp.state.current_state
        # qDebug(str(st))
        return self.is_connected

    def isPeerConnected(self, peer):
        # qDebug(str(self.fixstatus))
        return self.fixstatus[peer]

    def createChatroom(self, room_key, title):
        room_ident = '%s.%s' % (self.src_pname, room_key)
        room_ident = '%s.%s' % (self.src_pname, self._roomify_name(title))
        self.create_muc2(room_ident, title)
        return room_ident.lower()

    def groupInvite(self, group_number, peer):
        self.muc_invite(group_number, peer)
        return

    def groupNumberPeers(self, group_number):
        return self.muc_number_peers(group_number)

    # raw xmpp protocol handler
    def initXmpp(self):
        from .secfg import xmpp_user, xmpp_pass, peer_xmpp_user, xmpp_server
        self.self_user = xmpp_user
        self.peer_user = peer_xmpp_user
        self.xmpp_server = xmpp_server
        self.xmpp_conference_host = 'conference.' + xmpp_user.split('@')[1]

        loglevel = logging.DEBUG
        loglevel = logging.WARNING
        logging.basicConfig(level=loglevel, format='%(levelname)-8s %(message)s')

        self.nick_name = 'yatbot0inmuc'
        self.peer_jid = peer_xmpp_user
        self.is_connected = False
        self.fixrooms = defaultdict(list)
        self.fixstatus = defaultdict(bool)
        self.xmpp = sleekxmpp.ClientXMPP(jid=xmpp_user, password=xmpp_pass)

        self.xmpp.auto_authorize = True
        self.xmpp.auto_subscribe = True

        self.xmpp.register_plugin('xep_0030')
        self.xmpp.register_plugin('xep_0045')
        self.xmpp.register_plugin('xep_0004')
        self.plugin_muc = self.xmpp.plugin['xep_0045']

        self.xmpp.add_event_handler('connected', self.on_connected)
        self.xmpp.add_event_handler('connection_failed', self.on_connection_failed)
        self.xmpp.add_event_handler('disconnected', self.on_disconnected)

        self.xmpp.add_event_handler('session_start', self.on_session_start)
        self.xmpp.add_event_handler('message', self.on_message)
        self.xmpp.add_event_handler('groupchat_message', self.on_muc_message)
        self.xmpp.add_event_handler('groupchat_invite', self.on_groupchat_invite)
        self.xmpp.add_event_handler('got_online', self.on_muc_online)
        self.xmpp.add_event_handler('groupchat_presence', self.on_groupchat_presence)
        self.xmpp.add_event_handler('presence', self.on_presence)
        self.xmpp.add_event_handler('presence_available', self.on_presence_avaliable)

        qDebug(str(self.xmpp.boundjid.host) + '...........')
        self.start()

        return

    def run(self):
        qDebug('hhehehe')
        server = None
        # server = ('xmpp.jp', 5222)
        # server = ('b.xmpp.jp', 5222)
        if self.xmpp_server is not None and len(self.xmpp_server) > 0:
            server = tuple(self.xmpp_server.split(':'))
        if self.xmpp.connect(server, use_tls=True):
            self.xmpp.process(block=True)
            qDebug('Xmpp instance Done.')
        else:
            qDebug('unable to connect,' + str(self.jid))
        return

    def on_connected(self, what):
        qDebug('hreere:' + str(what))
        self.is_connected = True
        self.connected.emit()
        return

    def on_connection_failed(self):
        qDebug('hreere')
        self.is_connected = False
        self.disconnected.emit()
        return

    def on_disconnected(self, what):
        qDebug('hreere:' + str(what))
        self.is_connected = False
        self.disconnected.emit()
        return

    def on_session_start(self, event):
        qDebug('hhere:' + str(event))

        self.xmpp.send_presence()
        self.xmpp.get_roster()

        # self.xmpp.plugin['xep_0045'].joinMUC('yatest0@conference.xmpp.jp', 'yatbot0inmuc')
        # self.create_muc('yatest1')
        return

    def on_message(self, msg):
        qDebug(b'hhere:' + str(msg).encode())

        if msg['type'] in ('chat', 'normal'):
            # msg.reply("Thanks for sending 000\n%(body)s" % msg).send()
            # self.xmpp.send_message(mto=msg['from'], mbody='Thanks 国为 for sending:\n%s' % msg['body'])
            self.newMessage.emit(msg['body'])
        elif msg['type'] in ('groupchat'):
            mto = msg['from'].bare
            # print(msg['from'], "\n")
            # qDebug(mto)

            if msg['from'].resource == self.peer_jid.split('@')[0]:
                mgroup = msg['from'].user
                mbody = msg['body']
                self.newGroupMessage.emit(mgroup, mbody)
            else:  # myself send
                pass

            if msg['from'] != 'yatest1@conference.xmpp.jp/yatbot0inmuc' and \
               msg['from'] != 'yatest0@conference.xmpp.jp/yatbot0inmuc':
                pass
                # self.xmpp.send_message(mto=mto, mbody='Thanks 国为 for sending:\n%s' % msg['body'],
                #                       mtype='groupchat')
            else:
                pass

        # import traceback
        # traceback.print_stack()
        # qDebug('done msg...')
        return

    def on_muc_message(self, msg):
        # qDebug(b'hhere:' + str(msg).encode())

        #if msg['mucnick'] != self.nick and self.nick in msg['body']:
        #   qDebug('want reply.......')
            # self.send_message(mto=msg['from'].bare,
            #                  mbody="I heard that, %s." % msg['mucnick'],
            #                  mtype='groupchat')
        #    pass

        return

    def on_groupchat_invite(self, inv):
        qDebug(b'hreree:' + str(inv).encode())

        if inv['from'].bare == self.xmpp.boundjid:
            pass  # from myself
        else:
            room = inv['from'].bare
            muc_nick = self.nick_name
            self.plugin_muc.joinMUC(room, muc_nick)
            # self.groupInvite.emit(room)
        return

    def on_muc_online(self, presense):
        qDebug(b'hreree' + str(presense).encode())
        room = presense['from'].bare
        peer_jid = self.peer_jid
        reason = 'hello come here:' + room
        # mfrom = presense['to']

        qDebug(('muc room is:' + room).encode())
        if room == self.xmpp.boundjid:  # not a room
            qDebug(('not a valid muc room:' + room).encode())
            return

        qDebug(self.xmpp.boundjid.host)
        if room.split('@')[1] == self.xmpp.boundjid.host:
            qDebug(('not a valid muc room:' + room).encode())
            return

        form = self.plugin_muc.getRoomConfig(room)
        # print(form)
        # for f in form.field:
        #     print("%40s\t%15s\t%s" % (f, form.field[f]['type'], form.field[f]['value']))

        # http://xmpp.org/extensions/xep-0045.html#createroom-reserved
        form.field['muc#roomconfig_roomname']['value'] = "jioefefjoifjoife"
        form.field['muc#roomconfig_roomdesc']['value'] = "Script configured room"
        form.field['muc#roomconfig_persistentroom']['value'] = False
        form.field['muc#roomconfig_publicroom']['value'] = False
        form.field['public_list']['value'] = False
        form.field['muc#roomconfig_moderatedroom']['value'] = False
        form.field['allow_private_messages']['value'] = False
        # form.field['muc#roomconfig_enablelogging']['value'] = False
        form.field['muc#roomconfig_changesubject']['value'] = True
        form.field['muc#roomconfig_maxusers']['value'] = ('2')
        form.field['muc#roomconfig_membersonly']['value'] = True  # 只能邀请加入，出现407，需要怎么办呢？
        # TODO 调整配置参数后，首次邀请出现了报错，407需要注册。
        # self.plugin_muc.setAffiliation方法先把对方账号设置为成员。

        form.set_type('submit')
        self.plugin_muc.setRoomConfig(room, form)

        form = self.plugin_muc.getRoomConfig(room)
        # print(form)
        # for f in form.field:
        #    print("%40s\t%15s\t%s" % (f, form.field[f]['type'], form.field[f]['value']))

        # self.plugin_muc.invite(room, peer_jid, reason=reason)  # , mfrom=mfrom)

        # 可用的配置项列表
        #            FORM_TYPE                 hidden ['http://jabber.org/protocol/muc#roomconfig']
        #                muc#roomconfig_roomname            text-single
        #                muc#roomconfig_roomdesc            text-single
        #          muc#roomconfig_persistentroom                boolean False
        #              muc#roomconfig_publicroom                boolean True
        #                            public_list                boolean True
        #   muc#roomconfig_passwordprotectedroom                boolean False
        #              muc#roomconfig_roomsecret           text-private
        #                muc#roomconfig_maxusers            list-single 200
        #                   muc#roomconfig_whois            list-single moderators
        #             muc#roomconfig_membersonly                boolean False
        #           muc#roomconfig_moderatedroom                boolean True
        #                     members_by_default                boolean True
        #           muc#roomconfig_changesubject                boolean True
        #                 allow_private_messages                boolean True
        #   allow_private_messages_from_visitors            list-single anyone
        #                      allow_query_users                boolean True
        #            muc#roomconfig_allowinvites                boolean False
        #      muc#roomconfig_allowvisitorstatus                boolean True
        #  muc#roomconfig_allowvisitornickchange                boolean True
        #      muc#roomconfig_allowvoicerequests                boolean True
        # muc#roomconfig_voicerequestmininterval            text-single 1800
        #                      captcha_protected                boolean False
        #       muc#roomconfig_captcha_whitelist              jid-multi None
        #           muc#roomconfig_enablelogging                boolean True

        return

    def on_groupchat_presence(self, presence):
        qDebug(b'hreere' + str(presence).encode())
        return

    def on_muc_room_presence(self, presence):
        qDebug(b'hreere' + str(presence).encode())
        return

    def on_presence(self, presence):
        qDebug(b'hreere' + str(presence).encode())

        # qDebug(str(self.xmpp.roster))
        qDebug(str(self.xmpp.client_roster).encode())
        # qDebug(str(self.xmpp.client_roster['yatseni@xmpp.jp'].resources).encode())
        qDebug(str(self.xmpp.client_roster[self.peer_user].resources).encode())

        def check_self_presence(presence):
            if presence['to'] == presence['from']:
                return True
            return False

        def check_peer_presence(presence):
            if presence['from'].bare == self.peer_user:
                return True
            return False

        if check_self_presence(presence):
            self.is_connected = True
            self.connected.emit()
            return

        # peer user presence
        if check_peer_presence(presence):
            if presence['type'] == 'unavailable':
                for room in self.fixrooms:
                    if self.peer_user in self.fixrooms[room]:
                        self.fixrooms[room].remove(self.peer_user)
                self.fixstatus[self.peer_user] = False
                self.peerDisconnected.emit(self.peer_user)
            else:
                for room in self.fixrooms:
                    if self.peer_user not in self.fixrooms[room]:
                        # self.fixrooms[room].append(self.peer_user)
                        pass  # 这个地方不能再添加，对方掉线情况，需要使用invite才行。
                self.fixstatus[self.peer_user] = True
                self.peerConnected.emit(self.peer_user)
            return

        # 以下是关于room的presence处理
        room_jid = presence['from'].bare
        peer_jid = ''

        exp = r'jid="([^/]+)/\d+"'
        mats = re.findall(exp, str(presence))
        print(mats)
        if len(mats) == 0:
            # now care presence
            return

        # muc presence
        peer_jid = mats[0]
        if presence['type'] == 'unavailable':
            if peer_jid in self.fixrooms[room_jid]:
                self.fixrooms[room_jid].remove(peer_jid)
        else:
            onum = len(self.fixrooms[room_jid])
            if peer_jid not in self.fixrooms[room_jid]:
                self.fixrooms[room_jid].append(peer_jid)
            nnum = len(self.fixrooms[room_jid])
            if nnum == 2 and self.peer_user in self.fixrooms[room_jid]:
                user = presence['from'].user
                self.peerEnterGroup.emit(user)

        qDebug(str(self.fixrooms).encode())
        return

    def on_presence_avaliable(self, presence):
        qDebug(b'hreere' + str(presence).encode())
        return

    def create_muc(self, name):
        muc_name = '%s@%s' % (name, self.xmpp_conference_host)
        muc_nick = self.nick_name
        self.plugin_muc.joinMUC(muc_name, muc_nick)
        print(self.plugin_muc.rooms)
        return

    # TODO 检测聊天室是否已经存在，是否是自己创建的
    def create_muc2(self, room_jid, nick_name):
        muc_name = '%s@%s' % (room_jid, self.xmpp_conference_host)
        muc_nick = nick_name
        self.xmpp.add_event_handler('muc::%s::presence' % muc_name, self.on_muc_room_presence)
        qDebug((muc_name + ',,,' + muc_nick).encode())
        self.plugin_muc.joinMUC(muc_name, muc_nick)
        self.plugin_muc.setAffiliation(muc_name, jid=self.peer_user)
        print(self.plugin_muc.rooms, muc_name, self.xmpp.boundjid.bare)
        qDebug(str(self.plugin_muc.jidInRoom(muc_name, self.xmpp.boundjid.bare)))
        nowtm = QDateTime.currentDateTime()
        muc_subject = 'Chat with %s@%s since %s' \
                      % (nick_name, room_jid, nowtm.toString('H:m:ss M/d/yy'))
        # 设置聊天室主题
        self.xmpp.send_message(mto=muc_name, mbody=None,
                               msubject=muc_subject, mtype='groupchat')
        return

    def muc_invite(self, room_name, peer_jid):
        qDebug('heree')
        room_jid = '%s@%s' % (room_name, self.xmpp_conference_host)
        reason = 'hello come here:' + room_jid
        self.plugin_muc.invite(room_jid, peer_jid, reason=reason)  # , mfrom=mfrom)
        return

    def muc_number_peers(self, room_jid):
        muc_name = '%s@%s' % (room_jid.lower(), self.xmpp_conference_host)
        qDebug((muc_name + str(self.fixrooms)).encode())
        # room_obj = self.plugin_muc.rooms[muc_name]
        room_obj = self.fixrooms[muc_name]
        qDebug(str(room_obj) + '==len==' + str(len(room_obj)))
        for e in self.fixrooms:
            qDebug(str(e).encode())
        # qDebug(str(room_obj) + str(self.plugin_muc.rooms.keys()))
        # for room_name in self.plugin_muc.rooms:
        #    room_obj = self.plugin_muc.rooms[room_name]
        #    print(room_obj)
        return len(room_obj)

    def muc_send_message(self, room_name, msg):
        mto = '%s@%s' % (room_name, self.xmpp_conference_host)
        mbody = msg
        mtype = 'groupchat'
        qDebug(mto.encode())
        self.xmpp.send_message(mto=mto, mbody=mbody, mtype=mtype)
        return

    def send_message(self, peer_jid, msg):
        mto = peer_jid
        mbody = msg
        mtype = 'chat'
        self.xmpp.send_message(mto=mto, mbody=mbody, mtype=mtype)
        return

    # 把oname中的特殊字符转换为xmpp支持conference名
    # 主要思路是把特殊的符号过滤掉，手动替换为*
    # '"@&  => ****+
    def _roomify_name(self, oname):
        nname = ''
        for ch in oname:
            nch = ch
            if ch in ("'", '"', '@', '&'):
                nch = '*'
            elif ch in (' '):
                nch = '+'
            elif ch in ('<', '>', '(', ')'):
                nch = '.'
            elif ch in ('，'):  # 全角标点
                nch = ','
            elif ch in ('。'):
                nch = '.'
            nname += nch
        return nname


if __name__ == '__main__':
    pass
