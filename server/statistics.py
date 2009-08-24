from django.core.management import setup_environ
import settings
setup_environ(settings)
from server.feedme.models import *
import datetime
import sys
import numpy
from django.db.models import F

# We don't want to show up in statistics
admins = ['msbernst@mit.edu', 'marcua@csail.mit.edu',
          'karger@csail.mit.edu']

def generate_statistics(sharers, start_time, end_time):
    """Returns a dictionary of useful statistics for the sharers"""
    stats = dict()

    # unique sharing events
    # TODO: handle what happens when users switch to second half of study
    newposts = SharedPost.objects \
               .filter(
                 sharedpostreceiver__time__gte = start_time,
                 sharedpostreceiver__time__lt = end_time,
                 sharer__in = sharers
               ).filter(
                 sharedpostreceiver__time__gte = F('sharer__studyparticipant__studyparticipantassignment__start_time'),
                 sharedpostreceiver__time__lt = F('sharer__studyparticipant__studyparticipantassignment__end_time')
               ).distinct()
    stats['shared_posts'] = newposts.count()

    # emails with clickthroughs
    clicked = newposts.all() \
              .filter(clickthroughs__gte = 1)
    stats['clickthroughs'] = clicked.count()

    # emails with thanks
    thanked = newposts.all() \
              .filter(thanks__gte = 1)
    stats['thanks'] = thanked.count()
    
    # total number of people (not unique) shared with
    recipients = Receiver.objects \
              .filter(sharedpostreceiver__shared_post__in = newposts.all())
    stats['recipients'] = recipients.count()

    # unique number of people shared with
    unique_recipients = Receiver.objects \
              .filter(sharedpostreceiver__shared_post__in = newposts.all()) \
              .distinct()
    stats['unique_recipients'] = unique_recipients.count()

    # times GReader loaded in browser
    logins = LoggedIn.objects \
      .filter(
              time__gte = start_time,
              time__lt = end_time,
              sharer__in = sharers
             ).filter(
                time__gte = F('sharer__studyparticipant__studyparticipantassignment__start_time'),
                time__lt = F('sharer__studyparticipant__studyparticipantassignment__end_time')
             ).distinct()
    stats['logins'] = logins.count()

    # number of posts viewed
    viewed = ViewedPost.objects \
        .filter(
                time__gte = start_time,
                time__lte = end_time,
                sharer__in =  sharers
               ).filter(
                time__gte = F('sharer__studyparticipant__studyparticipantassignment__start_time'),
                time__lt = F('sharer__studyparticipant__studyparticipantassignment__end_time')
               ).distinct()
    stats['viewed'] = viewed.count()

    # number of viewed posts with a link clicked in the greader interface
    greader_clicked = viewed.all().filter(link_clickthrough = True)
    stats['greader_clicked'] = greader_clicked.count()

    return stats

def since(mode, num_days):
    sinceday = datetime.datetime.now() - datetime.timedelta(days = num_days)
    now = datetime.datetime.now()

    print "Printing %s report since %d days ago" % (mode, num_days)

    if (mode == "usersummary"):
        usersummary(sinceday, now)
    elif (mode == "groupsummary"):
        groupsummary(sinceday, now)
    else:
        print "Mode must be one of 'usersummary' or 'groupsummary'."

def usersummary(sinceday, now):
    participants = StudyParticipant.objects \
                    .exclude(sharer__user__email__in = admins)
    sharers = [sp.sharer for sp in participants]
    first = True
    keys = dict()
    for sharer in sharers:
        stats = generate_statistics([sharer], sinceday, now)
        if first:
            keys = stats.keys()
            print "name, email, study group, ui on, social on, %s" % (", ".join(keys))
            first = False
        name = sharer.name()
        email = sharer.user.email
        participant = StudyParticipant.objects.get(sharer = sharer)
        study_group = participant.study_group
        ui = participant.user_interface
        social = participant.social_features
        stats_str = ", ".join([str(stats[key]) for key in keys])
        print ("%s, %s, %s, %s, %s, %s" % (name, email, study_group, ui, social, stats_str)).encode('ascii', 'backslashreplace')

def groupsummary(sinceday, now):
    for i in range(4):
        user_interface = (i <= 1)
        social_features = ( i % 2 == 0 )
        print 'user interface: ' + str(user_interface)
        print 'social features: ' + str(social_features)
        sharers = Sharer.objects \
                  .filter(studyparticipant__user_interface = user_interface,
                          studyparticipant__social_features = social_features)\
                  .exclude(user__email__in = admins)
        all_stats = [generate_statistics([sharer], sinceday, now) for sharer in sharers]
        keys = all_stats[0].keys()
        print "For %d members:" % (sharers.count())
        for key in keys:
            vals = [stats[key] for stats in all_stats]
            median = numpy.median(vals)
            print "Median %s: %f" % (key, median)

if __name__ == "__main__":
    if len(sys.argv) == 3:
        mode = str(sys.argv[1])
        days = int(sys.argv[2])
        since(mode, days)
    else:
        print "Arguments: [usersummary|groupsummary] num-days"
