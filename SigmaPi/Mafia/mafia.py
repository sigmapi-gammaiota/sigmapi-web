
from .models import *

def _do_lynch(game):

    # If first day, no lynch
    if game.day_number == 1:
        result = MafiaDayResult(game=game, day_number=1, lynched=None)
        result.save()
        return

    # Collect players and votes, and make sure query sets match
    players = MafiaPlayer.objects.filter(
        game=game, status=MafiaPlayerStatus.ALIVE.code
    )
    votes = MafiaVote.objects.filter(
        voter__game=game, day_number=game.day_number
    )
    voters = set(vote.voter for vote in votes)
    if voters != set(players):
        raise MafiaError(
            'set of alive players doesn\'t match set of voters'
        )

    # Tally votes
    vote_tallies = {player.user: 0 for player in players}
    vote_tallies[None] = 0
    for vote in votes:
        voting_power = (
            3 if (
                vote.voter.role == MafiaRole.MAYOR.code and
                vote.voter.times_action_used >= 1
            ) else 1
        )
        if vote.vote_type == MafiaVoteType.ABSTAIN.code:
            continue
        elif vote.vote_type == MafiaVoteType.NO_LYNCH.code:
            vote_tallies[None] += voting_power
        elif vote.vote_type == MafiaVoteType.LYNCH.code:
            vote_tallies[vote.vote] += voting_power
        else:
            raise MafiaError('illegal value of MafiaVote.vote_type: ' + `vote`)

    # Calculate who to lynch
    lynchee = None
    max_votes = 0
    for user, num_votes in vote_tallies.iteritems():
        if num_votes > max_votes:
            lynchee = user
            max_votes = num_votes
        elif num_votes == max_votes:
            lynchee = None

    # Perform lynch, create result
    if lynchee:
        lynche_player = players.get(user=lynchee)
        lynche_player.status = MafiaPlayerStatus.LYNCHED.code
    result = MafiaDayResult(
        game=game, day_number=game.day_number, lynched=lynchee
    )
    result.save()

    # TODO: Sabateur and Jester stuff

def _clear_previous_results(game):
    MafiaNightResult.objects.filter(
        action__performer__game=game,
        action__night_number=game.day_number
    ).delete()

def _get_players_and_actions(game):
    players = MafiaPlayer.objects.filter(
        game=game, status=MafiaPlayerStatus.ALIVE.code
    )
    actions = MafiaAction.objects.filter(
        performer__game=game, night_number=game.day_number
    )
    performers = set(action.performer for action in actions)
    if performers != set(players):
        raise MafiaError(
            'set of alive players doesn\'t match set of action performers'
        )
    return players, actions

def _do_single_switch(switcher0, switcher1, target0, target1, switch_map, users_to_results):
    temp = switch_map[target0]
    switch_map[target0] = switch_map[target1]
    switch_map[target1] = temp
    users_to_results[target0].switched_with = target1
    users_to_results[target1].switched_with = target0
    users_to_results[target0].add_switched_by(switcher0)
    users_to_results[target1].add_switched_by(switcher1)
    switcher0.action_effective = True
    switcher1.action_effective = True

def _do_double_switch(switcher0, switcher1, target, users_to_results):
    users_to_results[target].switched_with = target
    users_to_results[target].add_switched_by(switcher0)
    users_to_results[target].add_switched_by(switcher1)
    switcher0.action_effective = True
    switcher1.action_effective = True

def _do_overlapping_switch(switcher0, switcher1, target0, overlapped_target, target1, users_to_results):
    _do_single_switch(switcher0, switcher1, target0, target1, users_to_results)
    _do_double_switch(switcher0, switcher1, overlapped_target, users_to_results)

def _do_switching(actions, results, users_to_results, actions_to_results):

    # Clear previous calculations
    for result in results:
        result.clear_switched_by()

    # Initialize switch map; collect switch action results
    switched = {result.player.user: result.player.user for result in results}
    switch_actions = actions.filter(action_type=MafiaActionType.SWITCH.code)
    switch_results = [actions_to_results[switch_action] for switch_action in switch_actions]

    # Fail if more than two switches
    if len(switch_results) > 2:
        raise MafiaError('more than two switch actions in single night')

    # Perform two switches
    if len(switch_results) >= 2:

        # Assign helper variables for switchers and targets
        s0 = switch_results[0].player.user
        s1 = switch_results[1].player.user
        s0t0 = switch_results[0].target0_after_control
        s0t1 = switch_results[0].target1_after_control
        s1t0 = switch_results[1].target0_after_control
        s1t1 = switch_results[1].target1_after_control

        # If both seduced_or_died, do nothing
        if switch_results[0].seduced_or_died and switch_results[1].seduced_or_died:
            pass

        # If one seduced_or_died, do the other
        elif switch_results[0].seduced_or_died:
            _do_single_switch(s1, s1, s1t0, s1t1, users_to_results)
        elif switch_results[1].seduced_or_died:
            _do_single_switch(s0, s0, s0t0, s0t1, users_to_results)

        # Switches with the same two players
        elif (s0t0 == s1t0 and s0t1 == s1t1) or (s0t0 == s1t1 and s0t1 == s1t0):
            _do_double_switch(s0, s1, s0t0, users_to_results)
            _do_double_switch(s0, s1, s0t1, users_to_results)

        # Switches where one players is in both
        elif s0t0 == s1t0:
            _do_overlapping_switch(s0, s1, s0t1, s0t0, s1t1, users_to_results)
        elif s0t0 == s1t1:
            _do_overlapping_switch(s0, s1, s0t1, s0t0, s1t0, users_to_results)
        elif s0t1 == s1t0:
            _do_overlapping_switch(s0, s1, s0t0, s0t1, s1t1, users_to_results)
        elif s0t1 == s1t1:
            _do_overlapping_switch(s0, s1, s0t0, s0t1, s1t0, users_to_results)

        # Independent switches
        else:
            _do_single_switch(s0, s0, s0t0, s0t1, users_to_results)
            _do_single_switch(s1, s1, s1t0, s1t1, users_to_results)

    # Perform single switch
    elif len(switch_results) >= 1 and not switch_results[0].seduced_or_died:
        s = switch_results[0].player.user
        _do_single_switch(
            s, s,
            switch_results[0].target0_after_control,
            switch_results[0].target1_after_control,
            users_to_results
        )

    # Return switch map
    return switched

def _do_seduction(actions, results, users_to_results, actions_to_results):
    seduce_map = {results.player.user: False for results in results}
    for seduce_action in actions.filter(action_type=MafiaActionType.SEDUCE.code):
        seduce_result = actions_to_results[seduce_action]
        if seduce_result.seduced_or_died:
            continue
        target_result = users_to_results[seduce_result.target0]
        target_result.attempted_seduced = True
        target_result.add_targeted_by(seduce_result.player.user)
        seduce_result.action_effective = True
    return seduce_map

def _kill_cancelled(killer_result, killed_set):
    return (
        (not killer_result.seduced) or
        (killer_result.died and not killer_result.player.user in killed_set)
    )

def _kill_if_alive(killer_result, target_result, killed_status, killed_set, users_to_results):
    if target_result.died and target_result.player.user not in killed_set:
        killer_result.action_effective = True
        return
    target_result.status = (
        MafiaNightStatus.TERMINATED
        if MafiaNightStatus.TERMINATD.code in [target_result.status, killed_status]
        else MafiaNightStatus.ATTACKED
    )
    if target_result.died:
        killer_result.action_effective = True
        killed_set.add(target_result.user)
    else:
        for protector in target_result.get_protected_by():
            users_to_results[protector].action_effective = True
        if target_result.action_type == MafiaActionType.BULLETPROOF_VEST.code:
            target_result.action_effective = True

def _process_actions(actions):

    # Generate results and map from users to results
    results = [MafiaNightResult(action=action) for action in actions]
    actions_to_results = {result.action: result for result in results}
    users_to_results = {result.player.user: result for result in results}

    # Do control, terminating those that try to control on-guard players
    control_actions = actions.filter(action_type=MafiaActionType.CONTROL.code)
    if len(control_actions) > 1:
        raise MafiaError('more than one control action_type in single night')
    if control_actions:
        control_result = actions_to_results[control_actions[0]]
        t0_result = users_to_results[control_result.target0]
        # If target0 on guard, terminate controller
        if t0_result.on_guard:
            control_result.attacked_status = MafiaNightStatus.TERMINATED.code
            t0_result.action_effective = True
        # Else, control target0 to target target1
        else:
            t0_result.controlled_to_target = control_result.target1

    # Kill players targeting on-guard players
    for result in results:
        action_type = MafiaActionType.get_instance(result.action_type)
        # If covert, cannot be killed by on-guard player; continue
        if action_type.is_covert:
            continue
        # If two targets, check if target1 is on guard
        if action_type.num_targets == 2:
            t1_result = users_to_results[result.target1_after_control.user]
            # If so, terminate performer
            if t1_result.on_guard:
                result.attacked_status = MafiaNightStatus.TERMINATED.code
                t1_result.action_effective = True
        # If one or more targets, check if target0 is on guard
        if action_type.num_targets >= 1:
            t0_result = users_to_results[result.target1_after_control.user]
            # If so, terminate performer
            if t0_result.on_guard:
                result.attacked_status = MafiaNightStatus.TERMINATED.code
                t0_result.action_effective = True
        # If action was direct offense, mark on-guard player as attacked
        if action_type.is_direct_offense:
            t0_result.attacked_status = MafiaNightStatus.ATTACKED.code

    # Repeat switching and seduction until we reach a stable state
    switched, seduced = None, None
    while True:
        new_switched = _do_switching(actions, results, users_to_results, actions_to_results)
        new_seduced = _do_seduction(actions, results, users_to_results, actions_to_results)
        stable = (new_switched == switched and new_seduced == seduced)
        switched = new_switched
        seduced = new_seduced
        if stable:
            break

    # Mark framed player results
    for frame_action in MafiaAction.objects.filter(action_type=MafiaActionType.FRAME.code):
        frame_result = actions_to_results[frame_action]
        if actions_to_results[frame_result].seduced_or_died:
            continue
        target_result = users_to_results[switched[frame_result.target0_after_control]]
        target_result.framed = True
        target_result.add_targeted_by(frame_result.player.user)

    # Mark protected player results
    for protect_action in MafiaAction.objects.filter(action_type=MafiaActionType.PROTECT.code):
        protect_result = actions_to_results[protect_action]
        if protect_result.seduced_or_died:
            continue
        target_result = users_to_results[switched[protect_result.target0_after_control]]
        target_result.add_protected_by(protect_result.player.user)

    # Mark defended player results
    for defend_action in MafiaAction.objects.filter(action_type=MafiaActionType.DEFEND.code):
        defend_result = actions_to_results[defend_action]
        if defend_result.seduced_or_died:
            continue
        target_result = users_to_results[switched[defend_result.target0_after_control]]
        target_result.defended = True
        target_result.add_targeted_by(defend_result.player.user)

    # Kill players that try to attack defended players
    for result in results:
        if result.died:
            continue
        action_type = MafiaActionType.get_instance(result.action_type)
        if action_type.is_direct_offense and not action_type.is_covert:
            for defender in target_result.get_defended_by():
                result.status = MafiaNightStatus.TERMINATED
                users_to_results[defender].status = MafiaNightStatus.TERMINATED.code
                users_to_results[defender].action_effective = True

    # Mark corrupted player results; kill corrupter if successful
    for corrupt_action in MafiaAction.objects.filter(action_type=MafiaActionType.CORRUPT.code):
        corrupt_result = actions_to_results[corrupt_action]
        if corrupt_result.seduced_or_died:
            continue
        target_result = users_to_results[switched[corrupt_result.target0_after_control]]
        target_result.attempted_corrupted = True
        target_result.add_targeted_by(corrupt_result.player.user)
        if target_result.corrupted:
            corrupt_result.status = MafiaNightStatus.TERMINATED.code

    # Perform all remaining killing actions and roles with same priority
    died_from_killing = set()

    # Killing action: Slay
    for slay_action in MafiaAction.objects.filter(action_type=MafiaActionType.SLAY.code):
        slay_result = users_to_results[slay_action]
        if _kill_cancelled(slay_result, died_from_killing):
            continue
        target_result = users_to_results[switched[slay_result.target0_after_control]]
        _kill_if_alive(
            slay_result, target_result, MafiaNightStatus.ATTACKED,
            died_from_killing, users_to_results
        )
        target_result.add_targeted_by(slay_result.player.user)

    # Killing action: Ambush
    for ambush_action in MafiaAction.objects.filter(action_type=MafiaActionType.AMBUSH.code):
        ambush_result = actions_to_results[ambush_action]
        if _kill_cancelled(ambush_result, died_from_killing):
            continue
        ambusher = ambush_result.player.user
        ambushee = ambush_result.target0
        for result in results:
            # The player dies in the ambush if:
            died_in_ambush = (
                # They aren't the ambusher, and either (a), (b), or (c)
                result.player.user != ambusher and (
                    # (a) Their first target is ambushed
                    result.target0 == ambushee or
                    # (b) Their second target is ambushed and their action wasn't Control
                    (
                        result.target1 == ambushee and
                        result.action_type != MafiaActionType.CONTROL.code
                    # (c) They're the ambushee and they didn't target anyone else
                    ) or (
                        result.player.user == ambushee and
                        result.target0 == None
                    )
                )
            )
            if died_in_ambush:
                _kill_if_alive(
                    ambush_result, result, MafiaNightStatus.ATTACKED,
                    died_from_killing, users_to_results
                )

    # Killing action: Snipe
    for snipe_action in MafiaAction.objects.filter(action_type=MafiaActionType.SNIPE.code):
        snipe_result = actions_to_results[snipe_action]
        if _kill_cancelled(snipe_result, died_from_killing):
            continue
        target_result = users_to_results[snipe_result.target0] # NOT SWITCHED OR CONTROLLED
        _kill_if_alive(
            snipe_result, target_result, MafiaNightStatus.TERMINATED,
            died_from_killing, users_to_results
        )
        target_result.add_targeted_by(snipe_result.player.user)

    # Killing action: Ignite
    for ignite_action in MafiaAction.objects.filter(action_type=MafiaActionType.IGNITE.code):
        ignite_result = actions_to_results[ignite_result]
        if _kill_cancelled(ignite_result, died_from_killing):
            continue
        for result in results:
            if result.player.doused:
                _kill_if_alive(
                    ignite_result, result, MafiaNightStatus.TERMINATED,
                    died_from_killing, users_to_results
                )
        break # Only need to do ignite once


    # Killing role: Bomb
    bomb_results = [result for result in results if result.player.role == MafiaRole.BOMB.code]
    if len(bomb_results) > 1:
        raise MafiaError('more than one bomb in game')
    if len(bomb_results) >= 1 and not _kill_cancelled(bomb_results[0], died_from_killing):
        for result in results:
            is_direct_offense = MafiaActionType.get_instance(result.action_type).is_direct_offense
            if is_direct_offense:
                _kill_if_alive(
                    bomb_results[0], result, MafiaNightStatus.TERMINATED,
                    died_from_killing, users_to_results
                )

    # Killing role: Saboteur
    # TODO

    # Killing role: Jester
    # TODO

    # Mark doused results
    for douse_action in MafiaAction.objects.filter(action_type=MafiaActionType.DOUSE.code):
        douse_result = actions_to_results[douse_action]
        if douse_result.seduced_or_died:
            continue
        target_result = users_to_results[switched[douse_result.target0_after_control]]
        target_result.doused = True
        target_result.add_targeted_by(douse_result.player.user)

    # Mark un-doused results
    for un_douse_action in MafiaAction.objects.filter(action_type=MafiaActionType.UN_DOUSE.code):
        un_douse_result = actions_to_results[un_douse_action]
        if un_douse_result.seduced_or_died:
            continue
        target_result = users_to_results[switched[un_douse_result.target0_after_control]]
        target_result.un_doused = True
        target_result.add_targeted_by(un_douse_result.player.user)

    # Mark disposed player results
    for dispose_action in MafiaAction.objects.filter(action_type=MafiaActionType.DISPOSE.code):
        dispose_result = actions_to_results[dispose_action]
        if dispose_result.seduced_or_died:
            continue
        target_result = users_to_results[switched[dispose_result.target0_after_control]]
        target_result.disposed = True
        target_result.add_targeted_by(dispose_result.player.user)
        if target_result.died:
            dispose_result.action_effective = True

    # Mark remembered player results
    for remember_action in MafiaAction.objects.filter(action_type=MafiaActionType.REMEMBER.code):
        remember_result = actions_to_results[remember_action]
        if remember_result.seduced_or_died:
            continue
        remember_result.remembered = remember_result.target0_after_control
        remember_result.action_effective = True

    return results

def _get_name(user):
    return user.first_name + ' ' + user.last_name

def _list_users(users):
    num_users = len(users)
    if num_users == 0:
        return 'nobody'
    elif num_users == 1:
        return _get_name(users[0])
    elif num_users >= 2:
        return ', '.join(
            _get_name(user) for user in users[:-1]
        ) + ', and ' + _get_name(users[-1])

def _investigate(investigator_result, target_result):
    target_role = MafiaRole.get_instance(target_result.role)
    guilty = (
        (target_role.faction == MafiaFaction.MAFIA and target_role != MafiaRole.GODFATHER) or
        (target_role == MafiaRole.MILLER) or
        target_result.framed
    )
    appears_guilty = (
        not guilty
        if investigator_result.action_type == MafiaActionType.INSANE_INVESTIGATE.code
        else guilty
    )
    return 'GUILTY' if appears_guilty else 'INNOCENT'

def _scrutinize(target_result):
    role = MafiaRole.get_instance(target_result.player.role)
    return len(0 for at in role.action_types if at.is_lethal) >= 1

def _follow(target_result, users_to_results):
    return '' # TODO
    #    _get_name(target_night.target0_after_control)
    #    if target_night.tar

def _watch(watcher_result, target_result):
    return '' # TODO
    #return _list_users(list(
    #    set(target_night.get_targeted_by()) - set([follower_night.player.user])
    #))

def _generate_reports(results):
    users_to_results = {result.player.user: result for result in results}
    for result in results:
        name0 = _get_name(result.target0) if result.target0 else None
        name1 = _get_name(result.target1) if result.target1 else None
        if result.died:
            result.add_report_line('YOU DIED!')
            continue
        if result.action_type == MafiaActionType.NO_ACTION.code:
            result.add_report_line(
                'You did not perform an action.'
            )
            if result.seduced:
                result.add_report_line(
                    'You were seduced.'
                )
        elif result.seduced:
            result.add_report_line(
                'You were seduced and forgot to perform your action.'
            )
        elif result.action_type == MafiaActionType.CONTROL.code:
            result.add_report_line(
                'You controlled ' + name0 +
                ' to target ' + name1 + '.'
            )
        elif result.action_type == MafiaActionType.ON_GUARD.code:
            result.add_report_line(
                'You went on guard' + (
                    ', killing at least one player.' if result.action_effective
                    else '.'
                )
            )
        elif result.action_type == MafiaActionType.SEDUCE.code:
            result.add_report_line(
                'You may have seduced ' + name0 + '.'
            )
        elif result.action_type == MafiaActionType.SWITCH.code:
            result.add_report_line(
                'You switched ' + name0 + ' and ' +
                _get_name(result.target1) + '.'
            )
        elif result.action_type == MafiaActionType.FRAME.code:
            result.add_report_line(
                'You framed ' + name0 + '.'
            )
        elif result.action_type in [MafiaActionType.INVESTIGATE.code, MafiaActionType.INSANE_INVESTIGATE.code]:
            result.add_report_line(
                'You investigated ' + name0 +
                ', and concluded that they are ' +
                _investigate(
                    result,
                    users_to_results[users_to_results[result.target0].switched_with]
                ) + '.'
            )
        elif result.action_type == MafiaActionType.SCRUTINIZE.code:
            result.add_report_line(
                'You scrutinized ' + name0 +
                ', and concluded that they are ' +
                _scrutinize(users_to_results[users_to_results[result.target0].switched_with]) +
                '.'
            )
        elif result.action_type == MafiaActionType.PROTECT.code:
            protect_target = users_to_results[result.target0]
            if protect_target.status == MafiaNightStatus.SAFE.code:
                result.add_report_line(
                    'You protected ' + name + ', but they were not attacked.'
                )
            elif protect_target.status == MafiaNightStatus.ATTACKED.code:
                result.add_report_line(
                    'You successfully protected ' + name0 +
                    ' from an attack.'
                )
            elif protect_target.status == MafiaNightStatus.TERMINATED.code:
                result.add_report_line(
                    'You protected ' + name0 + ', but they died anyway.'
                )
        elif result.action_type == MafiaActionType.DEFEND.code:
            defend_target = users_to_results[result.target0]
            if defend_target.status == MafiaNightStatus.SAFE.code:
                result.add_report_line(
                    'You defended ' + name + ', but they were not attacked.'
                )
            elif defend_target.status == MafiaNightStatus.ATTACKED.code:
                raise MafiaError("defended target was attacked but defender is alive")
            elif defend_target.status == MafiaNightStatus.TERMINATED.code:
                result.add_report_line(
                    'You defended ' + name0 + ', but they died anyway.'
                )
        elif result.action_type == MafiaActionType.BULLETPROOF_VEST.code:
            result.add_report_line("You used bulletproof vest.")
        elif result.action_type == MafiaActionType.CORRUPT.code:
            corrupt_target = users_to_results[result.target0]
            if corrupt_target.corrupted:
                raise MafiaError('Player corrrupted but corrupter not dead')
            else:
                result.add_report_line(
                    'You attempted to corrupt ' + name0 +
                    ', but they resisted or were protected.'
                )
        elif result.action_type == MafiaActionType.SLAY.code:
            slay_target = users_to_results[result.target0]
            if slay_target.status == MafiaNightStatus.SAFE:
                result.add_report_line(
                    'You attempted to slay ' + name + ', but they survived.'
                )
            else:
                result.add_report_line('You slayed ' + name + '.')
        elif result.action_type == MafiaActionType.AMBUSH:
            result.add_report_line(
                'You ambushed ' + name + (
                    ', killing at leaset one player.'
                    if result.action_effective
                    else ', but did not kill anyone.'
                )
            )
        elif result.action_type == MafiaActionType.SNIPE.code:
            result.add_report_line('You sniped ' + name + '.')
        elif result.action_type == MafiaActionType.IGNITE.code:
            result.add_report_line('You ignited.')
        elif result.action_type == MafiaActionType.SABOTAGE:
            pass # TODO
        elif result.action_type == MafiaActionType.DOUSE.code:
            result.add_report_line('You doused ' + name +'.')
        elif result.action_type == MafiaActionType.UN_DOUSE.code:
            result.add_report_line('You un-doused ' + name +'.')
        elif result.action_type == MafiaActionType.DISPOSE.code:
            role_name = MafiaRole.get_instance(users_to_results[result.target0].role).name
            result.add_report_line(
                'You disposed ' + name + '. Their actual role is ' + role_name + '.'
                if result.action_effective
                else 'You attempted to dispose ' + name  + ', but they did not die.'
            )
        elif result.action_type == MafiaActionType.REVEAL.code:
            result.add_report_line('You revealed youself as Mayor.')
        elif result.action_type == MafiaActionType.FOLLOW.code:
            result.add_report_line(
                'You followed ' + name + ', and determined that they targeted ' +
                _follow(users_to_results[result.target]) + '.'
            )
        elif result.action_type == MafiaActionType.WATCH.code:
            result.add_report_line(
                'You watched ' + name + ', and determined that they were targeted by ' +
                _watch(users_to_results[result.target]) + '.'
            )
        elif result.action_type == MafiaActionType.REMEMBER.code:
            new_role = MafiaPlayer.objects.get(user=result.target0).role
            result.add_report_line(
                'You have remembered yourself as ' + _get_name(result.target0) + '. ' +
                'You are now a ' + MafiaRole.get_instance(new_role).name + '!'
            )

    # TODO: received action reporting

def _apply_results(players, results):
    pass # TODO

def advance_game(game):

    if game.time == MafiaGameTime.DAY.code:
        _do_lynch(game)
        game.time = MafiaGameTime.NIGHT.code
        return True

    elif game.time == MafiaGameTime.NIGHT.code:
        try:
            _clear_previous_results(game)
            players, actions = _get_players_and_actions(game)
            results = _process_actions(actions)
            _generate_reports(results)
            for result in results:
                result.save()
            _apply_results(players, results)
            for player in players:
                player.save()
        except MafiaError as e:
            print 'Mafia: Error while processing night: ' + e.message
            return False
        game.day_number += 1
        game.time = MafiaGameTime.DAY.code
        return True

    else:
        raise ValueError("invalid value of game.time: " + `game.time`)

def start_game(game):
    if game.day_number == 0:
        game.day_number = 1
        game.time = MafiaGameTime.DAY.code
    else:
        raise MafiaError('start_game: day_number must == 0')