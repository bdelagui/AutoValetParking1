car_pos_transitions_list = [(1,[1,2]),
                            (2,[2,3]),
                            (3,[3,4]),
                            (4,[4,5,12]),
                            (5,[5,6,12]),
                            (6,[6,7,13]),
                            (7,[7,8,14]),
                            (8,[8,9,15]),
                            (9,[9,10,16]),
                            (10,[10,11,17]),
                            (11,[11,17]), 
                            (12,[12,13,7]),
                            (13,[13,14,8]),
                            
                            (14,[14,15]),
                            (15,[15,16]),
                            (16,[16,17,27]),
                            
                            
                            (48,[48,28]), #parking state
                            (49,[49,31]), #parking state
                            (50,[50,33]), #parking state
                            
                            (17,[17,18,27]),
                            (18,[18,19,28]),
                            (19,[19,20,29]),
                            (20,[20,21,30]),
                            (21,[21,22,31]),
                            (22,[22,23,32]),
                            (23,[23,24,33]),
                            (24,[24,25,34]),
                            (25,[25,26,35,43]), # removed 43
                            (26,[26,37,43]), # removed 43
                            
                            (27,[27,28,48]),
                            (28,[28,29,20]),
                            (29,[29,30,21]),
                            (30,[30,21,31,49]),
                            
                            (31,[31,23,32]),
                            (32,[32,33]),
                            (33,[33,34,25,50]),
                            (34,[34,35,26]),
                            (35,[35,36,26]),
                            (36,[36,37,26]),
                            (37,[37,38,43]), #removed 43
                            
                            (38,[38,39,44]),
                            (39,[39,40,45]),
                            (40,[40,41,46]),
                            (41,[41,42,47]),
                            (42,[42,46,47]),
                            (43,[43,44,39]),
                            (44,[44,45,40]),
                            (45,[45,46,41]),
                            (46,[46,47,54]),
                            (47,[47,65,54]),
                            
                            (51,[51,52,62]), #parking state
                            (52,[52,53]), #parking state
                            (53,[53,64]), #parking state
                            
                            (54,[54,55,66]),
                            (55,[55,56,67]),
                            (56,[56,57,68]),
                            (57,[57,58,69]),
                            (58,[58,59,70]),
                            (59,[59,60,71]),
                            (60,[60,61,72]),
                            (61,[61,62,73]),
                            (62,[62,63,74]),
                            (63,[63,64,75]),
                            (64,[64,77,78,88]),
                            (65,[65,66,55]),
                            (66,[66,67,56,51]),
                            (67,[67,68,51,57]),
                            (68,[68,69,59]),
                            (69,[69,70,59,52]),
                            (70,[70,71,60]), 
                            (71,[71,72,61]),
                            (72,[72,73,53,62]),
                            (73,[73,74,63]),
                            (74,[74,75,64]),
                            (75,[75,76,64]),
                            (76,[76,77,64]),
                            
                            (77,[77,78,88]),
                            (78,[78,79,89]),
                            (79,[79,80,90]),
                            (80,[80,81,91]),
                            (81,[81,82,92]),
                            (82,[82,83,93]),
                            (83,[83,84,94]),
                            (84,[84,85,95]),
                            (85,[85,86,96]),
                            (86,[86,87]),
                            (87,[87,98]),
                            
                            (88,[88,89,79]),
                            (89,[89,90,80]),
                            (90,[90,91,81]),
                            (91,[91,92,82]),
                            (92,[92,93,83]),
                            (93,[93,94,84]),
                            (94,[94,95,85]),
                            (95,[95,96,86]),
                            (96,[96,97]),
                            (97,[87]),
                            (98,[98,99]),
                            (99,[99,100]),
                            (100,[100])]

car_status_transitions_list = [(1,[4]),(2,[2,3]),(3,[2]),(4,[3,4])]

# List of parking spots:
parking_spots = [48,49,50,51,52,53]

