"""
Copyright 2019 (c) GlibGlob Ltd.
Author: Laurence Psychic
Email: vesper.porta@protonmail.com

Initiate the VesperRPG System.
"""

import time

import tkinter as tk
from tkinter import ttk

from threading import Thread

from character import PlayerCharacter, Binding, create_object
from factories import load_game_data, load_stat_csv
from models import rpg_const, RpgTick
from rpg_util import Middleware


class VesperRpgSystem(Thread):
    """
    Class to manage the continuous processing of VesperRpg System in a separate
    thread.
    """

    def run(self):
        """
        Method run on initialisation as a Thread object.
        """
        while rpg_const.SYSTEM_ACTIVE:
            RpgTick.all_tock()
            time.sleep(1 / rpg_const.FPS_MAX)


class ErrorMiddleware(Middleware):
    """
    Manage the action handling from VesperRpg System.
    Toggle the inventory from show to hide.
    """
    name = ''
    callback = None

    def action(self, *args, chain_return=None, **kwargs):
        """
        Manage errors being returned from VesperRpg System.

        :param chain_return: None or dict when a response is expected.
        :return: Expected responce from handler or None.
        """
        rtn = self.callback(*args, chain_return=chain_return, **kwargs)
        return rtn

    def __init__(self, callback):
        if not callback:
            raise Exception('Initialisation argument not passed.')
        self.callback = callback
        super().__init__('Error')


class InventoryToggleMiddleware(Middleware):
    """
    Manage the action handling from VesperRpg System.
    Toggle the inventory from show to hide.
    """
    name = ''
    callback = None

    def action(self, *args, chain_return=None, **kwargs):
        """
        Show the inventory.
        Passing in a dictionary as `chain_return` the handlers are able to
        return data backk into the VesperRpg System as a mutable object, if the
        system is expecting data back then the data will be managed internally
        to the system, the default is not return object is supplied as default.

        :param chain_return: None or dict when a response is expected.
        :return: Expected responce from handler or None.
        """
        rtn = self.callback(*args, chain_return=chain_return, **kwargs)
        return rtn

    def __init__(self, callback):
        if not callback:
            raise Exception('Initialisation argument not passed.')
        self.callback = callback
        super().__init__('Inventory Toggle')


class CharacterSheetToggleMiddleware(Middleware):
    """
    Manage the action handling from VesperRpg System.
    Toggle the inventory from show to hide.
    """
    name = ''
    callback = None

    def action(self, *args, chain_return=None, **kwargs):
        """
        Show the inventory.
        Passing in a dictionary as `chain_return` the handlers are able to
        return data backk into the VesperRpg System as a mutable object, if the
        system is expecting data back then the data will be managed internally
        to the system, the default is not return object is supplied as default.

        :param chain_return: None or dict when a response is expected.
        :return: Expected responce from handler or None.
        """
        rtn = self.callback(*args, chain_return=chain_return, **kwargs)
        return rtn

    def __init__(self, callback):
        if not callback:
            raise Exception('Initialisation argument not passed.')
        self.callback = callback
        super().__init__('Character Sheet Toggle')


class ObjectItemLoadMiddleware(Middleware):
    """
    Manage the action handling from VesperRpg System.
    Load ObjectItem data.
    """

    def action(self, *args, chain_return=None, **kwargs):
        """
        Load data for an ObjectItem and represent on the provided object.

        :param chain_return: None or dict when a response is expected.
        :return: Expected responce from handler or None.
        """
        print(*args, chain_return, kwargs)
        return chain_return

    def __init__(self):
        super().__init__('ObjectItem Load')


class PlayerCharacterLoadMiddleware(Middleware):
    """
    Manage the action handling from VesperRpg System.
    Load PlayerCharacter data.
    """

    def action(self, *args, chain_return=None, **kwargs):
        """
        Load data for an PlayerCharacter and represent on the provided object.

        :param chain_return: None or dict when a response is expected.
        :return: Expected responce from handler or None.
        """
        print(*args, chain_return, kwargs)
        return chain_return

    def __init__(self):
        super().__init__('PlayerCharacter Load')


class VesperRpgSystemSaveMiddleware(Middleware):
    """
    Manage the action handling from VesperRpg System.
    Save PlayerCharacter data.
    """

    def action(self, *args, chain_return=None, **kwargs):
        """
        Save data for an PlayerCharacter.

        :param chain_return: None or dict when a response is expected.
        :return: Expected responce from handler or None.
        """
        print(*args, chain_return, kwargs)
        return chain_return

    def __init__(self):
        super().__init__('VesperRpg System Save')


class PlayerCharacterVectoriddleware(Middleware):
    """
    Manage the action handling from VesperRpg System.
    PlayerCharacter movement keys changed and vector update.
    """
    callback = None

    def action(self, *args, chain_return=None, **kwargs):
        """
        Movement changes for an PlayerCharacter.

        :param chain_return: None or dict when a response is expected.
        :return: Expected responce from handler or None.
        """
        rtn = self.callback(*args, chain_return=chain_return, **kwargs)
        return rtn

    def __init__(self, callback):
        if not callback:
            raise Exception('Initialisation argument not passed.')
        self.callback = callback
        super().__init__('PlayerCharacter Vector')


class Application(tk.Frame):
    """
    Runtime to manage window for shel to encapsulate inputs into
    VesperRpg System
    """
    rpg_system = None
    handle_bindings = True

    def binding(self, event):
        if not self.handle_bindings:
            return
        mode = str(event.type)
        if mode == 'KeyPress':
            rpg_const.PLAYER.binding_down(event.char)
        elif mode == 'KeyRelease':
            rpg_const.PLAYER.binding_up(event.char)

    def bind_keys(self):
        """
        Bind all key bindings from this application.
        """
        self.master.bind('<Enter>', self.binding)
        self.master.bind('Button1<KeyPress>', self.binding)
        self.master.bind('Button2<KeyPress>', self.binding)
        self.master.bind('Button3<KeyPress>', self.binding)
        self.master.bind('Button1<KeyRelease>', self.binding)
        self.master.bind('Button2<KeyRelease>', self.binding)
        self.master.bind('Button3<KeyRelease>', self.binding)
        self.master.bind('<MouseWheel>', self.binding)
        for o in range(255):
            try:
                key = ascii(chr(o)).replace("'", '')
                self.master.bind('{}<KeyPress>'.format(key), self.binding)
                self.master.bind('{}<KeyRelease>'.format(key), self.binding)
            except Exception:
                pass

    def unbind_keys(self):
        """
        Unbind all key bindings from this application.
        """
        self.master.unbind('<Enter>')
        self.master.unbind('Button1<KeyPress>')
        self.master.unbind('Button2<KeyPress>')
        self.master.unbind('Button3<KeyPress>')
        self.master.unbind('Button1<KeyRelease>')
        self.master.unbind('Button2<KeyRelease>')
        self.master.unbind('Button3<KeyRelease>')
        self.master.unbind('<MouseWheel>')
        for o in range(255):
            try:
                key = ascii(chr(o)).replace("'", '')
                self.master.unbind('{}<KeyPress>'.format(key))
                self.master.unbind('{}<KeyRelease>'.format(key))
            except Exception:
                pass

    def focus_inputs(self, event):
        """
        Stop and start the key capture on focusing on text entry.
        """
        mode = str(event.type)
        if mode == 'FocusIn':
            self.handle_bindings = False
        elif mode == 'FocusOut':
            self.handle_bindings = True

    def error_handler(
        self, error_type, obj, *args, chain_return=None, **kwargs
    ):
        """
        Handle errors reported from VesperRpg System ensuring the external game
        system is aware of failed interactions.
        """
        print(error_type, obj, *args, chain_return, **kwargs)
        return chain_return

    def inventory_toggle(self, *args, chain_return=None, **kwargs):
        """
        Show and hide the inventory screen.

        :param chain_return: None or dict when a response is expected.
        :return: Expected responce from handler or None.
        """
        length = len(args)
        if not length:
            return
        player_character = args[0]
        show_all = args[1] if length > 1 else True
        prefix = '| '
        parts = player_character.body.list_wears()
        rtn = '{}{}\'s Worn Items:\n'.format('', player_character.name)
        for part in parts:
            if show_all or part.wears.quantity > 0:
                for item in part.wears.items:
                    rtn += item.inspect(prefix=prefix, show_all=show_all)
        containers = player_character.body.list_contains()
        rtn += '{}{}\'s Containers and Items:\n'.format(
            '', player_character.name)
        for container in containers:
            if show_all or container.contains.quantity > 0:
                for item in container.contains.items:
                    if container in player_character.manipulators:
                        index = player_character.manipulators.index(container)
                        ready_is = player_character.readied[index]
                        ready_is = 'Not ' if not ready_is else ''
                        rtn += '{} is {}Ready'.format(container.name, ready_is)
                    rtn += item.inspect(prefix=prefix, show_all=show_all)
        self.output.set(rtn)
        print(rtn)

    def character_sheet_toggle(self, *args, chain_return=None, **kwargs):
        """
        Show and hide the inventory screen.

        :param chain_return: None or dict when a response is expected.
        :return: Expected responce from handler or None.
        """
        if not len(args):
            return
        player_character = args[0]
        rtn = '\n'
        rtn += 'Character "{}"\n'.format(player_character.name)
        rtn += 'Species "{}: {}"\n'.format(
            player_character.character.body.species,
            player_character.character.body.gender.name
        )
        rtn += ' - Level: {}\n'.format(player_character.level)
        for ind in player_character.character.indicators:
            rtn += ' - {}: {} / {} - \n'.format(
                ind.type.name, ind.value, ind.max)
        rtn += '\n'
        rtn += '----\n{} - remaining: {}\n{}\n{}\n'.format(
            player_character.character.stats.name,
            player_character.character.stats.remaining,
            str(
                [
                    (s.name, s.total)
                    for s in player_character.character.stats_soul.stats
                ]
            )[1:-1],
            str(
                [
                    (s.name, s.total)
                    for s in player_character.character.body.stats.stats
                ]
            )[1:-1],
        )
        repr_dict = {}
        for stat in player_character.character.disciplines.stats:
            name = stat.type.name
            if type(name) is list:
                name = '+'.join(name)
            if name not in repr_dict.keys():
                repr_dict[name] = []
            repr_dict[name].append(str((stat.name, stat.total)))
        rtn += '----\n{} - remaining: {}\n{}\n'.format(
            player_character.character.disciplines.name,
            player_character.character.disciplines.remaining,
            str(repr_dict)[1:-1].replace('], \'', ']\n\''),
        )
        repr_dict = {}
        for stat in player_character.character.skills.stats:
            name = stat.type.name
            if type(name) is list:
                name = '+'.join(name)
            if name not in repr_dict.keys():
                repr_dict[name] = []
            repr_dict[name].append(str((stat.name, stat.total)))
        rtn += '----\n{} - remaining: {}\n{}\n'.format(
            player_character.character.skills.name,
            player_character.character.skills.remaining,
            str(repr_dict)[1:-1].replace('], \'', ']\n\''),
        )
        self.output.set(rtn)
        print(rtn)
        return chain_return

    def object_vector_handler(self, *args, chain_return=None, **kwargs):
        """
        Update an object and provide collision detection to assert a force
        related to the amount of force being exerted back.

        :param chain_return: None or dict when a response is expected.
        :return: Expected responce from handler or None.
        """
        # print('object_vector_handler', *args, chain_return, kwargs)
        character = args[0]
        # print(character.name, character.vector)

    def close_app(self):
        """
        Close the application and shut down all threads.
        """
        self.unbind_keys()
        rpg_const.PLAYER.binding_down('VesperRpg System Exit')
        self.master.destroy()

    def create_char(self):
        """
        Create a new body for the player's character.
        """
        self.output.set('Your new life starts, just press \'h\' for help')
        rpg_const.PLAYER.birth(name=self.contents.get())
        self.contents.set('Character Name.')
        armour = create_object('Armoured Vest')
        gun = create_object('Deasert Eagle')
        psy = create_object('Ice Spikes')
        rpg_const.PLAYER.wear_item(armour)
        rpg_const.PLAYER.add_item(gun, part=rpg_const.PLAYER.left_hand)
        rpg_const.PLAYER.add_item(psy, part=rpg_const.PLAYER.right_hand)
        rpg_const.PLAYER.vector.position = (0, 0, 0, )

    def kill_char(self):
        """
        Kill the player's character.
        """
        name = rpg_const.PLAYER.name
        rpg_const.PLAYER.death()
        self.output.set('{}, You\'re Dead.'.format(name))

    def send_cmd(self):
        command = self.complex_comand.get()
        cmd_list = command.split()
        value_1 = ' '.join(cmd_list[1:-1])
        value_2 = cmd_list[-1:][0]
        command = 'm ' + cmd_list[0]
        rpg_const.PLAYER.binding_down(command, value_1, value_2)
        self.complex_comand.set('Allocate.')

    def create_widgets(self):
        """
        Create the required user interface elements in Application to interact
        with VesperRpg System.
        """
        self.output = tk.StringVar()
        self.output.set('')
        self.output_text = tk.Entry(textvariable=self.output, width=400)
        self.output_text.pack(side='top')

        self.complex_comand = tk.StringVar()
        self.complex_comand.set('Allocate.')
        self.complex_input = ttk.Entry(textvariable=self.complex_comand)
        self.complex_input.pack(side='top')
        self.complex_input.bind('<FocusIn>', self.focus_inputs)
        self.complex_input.bind('<FocusOut>', self.focus_inputs)

        self.contents = tk.StringVar()
        self.contents.set('Character Name.')
        self.character_name = ttk.Entry(textvariable=self.contents)
        self.character_name.pack(side='top')
        self.character_name.bind('<FocusIn>', self.focus_inputs)
        self.character_name.bind('<FocusOut>', self.focus_inputs)

        self.send_cmd = tk.Button(
            self, text='Send Complex Command', command=self.send_cmd)
        self.send_cmd.pack(side='top')

        self.create_char = tk.Button(
            self, text='Create Character', command=self.create_char)
        self.create_char.pack(side='top')

        self.create_char = tk.Button(
            self, text='Kill Character', command=self.kill_char)
        self.create_char.pack(side='top')

        self.quit = tk.Button(
            self, text='X', fg='red', command=self.close_app)
        self.quit.pack(side='bottom')

    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.bind_keys()
        self.pack()
        self.create_widgets()
        self.rpg_system = VesperRpgSystem()
        self.rpg_system.start()
        ErrorMiddleware(self.error_handler)
        InventoryToggleMiddleware(self.inventory_toggle)
        CharacterSheetToggleMiddleware(self.character_sheet_toggle)
        ObjectItemLoadMiddleware()
        PlayerCharacterLoadMiddleware()
        VesperRpgSystemSaveMiddleware()
        PlayerCharacterVectoriddleware(self.object_vector_handler)


def main():
    """
    Main method for application
    Just press 'h' for help.
    """
    app_name = '- Vesper RPG System -'
    print(app_name)
    # TODO: Thread game data loading and have a float value to wait for 1.
    load_game_data()
    Binding.DEFAULT = load_stat_csv('bindings', row_data=True)
    rpg_const.TURN_BASED = False
    rpg_const.PLAYER = PlayerCharacter(npc=False)
    root = tk.Tk()
    app = Application(master=root)
    app.master.title(app_name)
    app.master.minsize(1000, 400)
    app.master.maxsize(1000, 400)
    app.mainloop()


if __name__ == '__main__':
    main()
