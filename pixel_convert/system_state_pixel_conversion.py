#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug  4 23:20:03 2020

@author: berlindelaguila
"""



abstr_to_pixel = {1:((120,130),(60,65)),
                2:((135,145),(60,65)),
                3:((150,160),(60,65)),
                4:((155,165),(60,65)),
                5:((175,180),(65,75)),
                6:((175,180),(80,90)),
                7:((175,180),(95,105)),
                8:((175,180),(110,120)),
                9:((175,180),(125,135)),
                10:((170,175),(65,75)),
                11:((170,175),(80,90)),
                12:((170,175),(95,105)),
                13:((170,175),(110,120)),
                14:((170,175),(125,135)),
                15:((170,175),(140,150)),
                16:((155,165),(140,150)),
                17:((140,150),(140,155)),
                18:((125,140),(140,155)),
                19:((110,120),(140,155)),
                20:((95,105),(140,155)),
                21:((80,90),(140,155)),
                22:((65,75),(140,155)),
                23:((50,60),(140,155)),
                24:((35,45),(140,155)),
                25:((20,30),(140,155)),
                26:((10,20),(155,165)),
                27:((10,15),(170,180)),
                28:((10,15),(185,195)),
                29:((10,15),(200,210)),
                30:((15,25),(210,220)),
                
                31:((30,40),(220,225)),
                32:((45,55),(220,225)),
                33:((55,65),(220,225)),
                34:((75,85),(220,225)),
                35:((90,100),(220,225)),
                36:((105,115),(220,225)),
                37:((120,130),(220,225)),
                38:((135,145),(220,225)),
                39:((150,160),(220,225)),
                40:((165,175),(220,225)),
                41:((180,190),(220,225)),
                
                42:((195,205),(205,215)),
                43:((190,200),(205,215)),
                44:((200,205),(190,200)),
                45:((200,205),(175,185)),
                46:((200,205),(160,170)),
                47:((200,205),(145,155)),
                48:((200,205),(130,140)),
                49:((200,205),(115,125)),
                50:((200,205),(100,110)),
                51:((200,205),(85,95)),
                52:((200,205),(70,80)),
                53:((200,205),(55,65)),
                
                54:((205,210),(190,200)),
                55:((205,210),(175,190)),
                56:((205,210),(160,170)),
                57:((205,210),(145,155)),
                58:((205,210),(130,140)),
                59:((205,210),(115,125)),
                60:((205,210),(100,110)),
                61:((205,210),(85,95)),
                62:((205,210),(70,80)),
                63:((210,215),(60,70)),                
                64:((220,230),(55,60)),
                65:((235,245),(55,60)),
                66:((250,260),(55,60))}

       
# pixels to abstract 
pixels_to_abstr = {v: k for k, v in abstr_to_pixel.items()}
#print(pixels_to_abstr)

x_bounds = dict()
y_bounds = dict()
midpoint = dict()
for keys, vals in abstr_to_pixel.items():
    x_bounds[keys] = vals[0]
    y_bounds[keys] = vals[1]
    midpoint[keys] = ((vals[0][0] + vals[0][1])/2, (vals[1][0] + vals[1][1])/2) # stores (xmid, ymid) for each abstract state
    #print(x_bounds,'\n')
    #print(y_bounds,'\n')
    #print(midpoint,'\n')

def convert_to_pixels(keys):    
   return (keys, midpoint[keys])

print(convert_to_pixels(66))



pixel_range = dict()

for pixel_keys, state_vals in pixels_to_abstr.items():
    pixel_range[pixel_keys] = state_vals 


def convert_to_abstr(pixel_keys):
    return(pixel_range[pixel_keys])
    
print(convert_to_abstr(((250,260),(55,55))))

    
    

        