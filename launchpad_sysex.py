import mido
import math
import time
import numpy as np

from mido import Message
from scipy import signal
from matplotlib import cm

""" Useful to find your Launchpad port names """
print(mido.get_output_names())
print(mido.get_input_names())

""" Declaring Launchpad X ports """
outport = mido.open_output('MIDIOUT2 (LPX MIDI) 4')
inport = mido.open_input('MIDIIN2 (LPX MIDI) 3')

def rgb_data(led_indexes, rgb):
    """ Creates the data array for RGB lighting mode """
    data =[]
    for i, led_index in enumerate(led_indexes):
        data += [3, led_index, rgb[i][0], rgb[i][1], rgb[i][2]]
    return data

def from_xy_to_note(x, y):
    """ Convert XY to programmer 4 layout """
    note = x + y *10
    return note

def from_note_to_xy(note):
    """ Convert programmer 4 layout note values to XY """
    x = note % 10 - 1
    y = math.floor(note / 10) - 1
    return x, y

def gkern(kernlen=9, std=1.5):
    """Returns a 2D Gaussian kernel array."""
    gkern1d = signal.gaussian(kernlen, std=std).reshape(kernlen, 1)
    gkern2d = np.outer(gkern1d, gkern1d)
    return gkern2d

head = [0, 32, 41, 2, 12, 3] # Lighting head message, constant
my_cmap  = cm.get_cmap('rainbow') # Matplotlib colormap to match colors to velocity
led_indexes = [(x+1) + 10*(y+1) for x in range(9) for y in range(9)] # Recreate the indexes of the layout 4

original_frame = np.zeros((9, 9, 3)) # Rest frame (colors will always converge towards it)
gkern = gkern() # Compute the 9x9 gaussian 9x9, you can change the std for bigger of smaller gaussians.
frame = original_frame # Set the current frame to rest frame

''' Live loop '''
while True:
    ''' Iterate on message in a non-blocking way '''
    for msg in inport.iter_pending():
        if msg.type == 'note_on' and msg.velocity > 0:
            x, y = from_note_to_xy(msg.note) # Convert note from launchpad to XY
            rgb_hit = my_cmap(msg.velocity/127.0) # Convert velocity to RGB
            modifier = np.ones((9, 9, 3)) # Declare a modifier (a color layer)
            ''' Set the color of the gaussian from the rgb hit and the gaussian kernel '''
            modifier[:, :, 0] = 127 * rgb_hit[0] * gkern
            modifier[:, :, 1] = 127 * rgb_hit[1] * gkern
            modifier[:, :, 2] = 127 * rgb_hit[2] * gkern
            ''' Translate the gaussian according to the hit position '''
            modifier = np.roll(modifier, x-4, axis=0)
            modifier = np.roll(modifier, y-4, axis=1)
            frame = frame + modifier # Add the blob to the current frame

    frame += 0.1*(original_frame - frame) # Linearly converge toward rest frame
    frame[np.where(frame > 127)]=127 # Make sure you don't go outside domain
    frame_resh = frame.reshape(-1, frame.shape[-1]).astype(np.int) # Reshape frame in array of colors
    msg = Message('sysex', data= head + rgb_data(led_indexes, frame_resh)) # Construct SysEX message
    outport.send(msg)  # Send message
    time.sleep(1/100.) # Set the refreshing rate
