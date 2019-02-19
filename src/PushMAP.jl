import Base: ==, +, *, -


using POMDPs
using POMDPModels
using BasicPOMCP
using POMDPPolicies
using POMDPSimulators
using ParticleFilters
import ParticleFilters: BasicParticleFilter, UnweightedParticleFilter, SIRParticleFilter
using Distributions
using Random
import POMDPs: initialstate_distribution, actions, n_actions, reward, generate_s, discount, isterminal, transition, observation, generate_o
using POMDPModelTools
import POMDPModelTools: obs_weight



mutable struct MAP_Push_POMDP <: POMDPs.POMDP{Vector{Float64},Int,Vector{Int64}}
    discount_factor::Float64
    found_r::Float64
    lost_r::Float64
    step_size::Float64
    movement_cost::Float64
end


global robotViewRadius



function initialstate_distribution(pomdp::MAP_Push_POMDP,s::Vector{Int64})

	numMixands = 10000; 
	mixands = MvNormal[]; 
	for i=1:numMixands
		tmp = MvNormal([s[1],s[2],rand(10:427),rand(10:744)],[0.01,0.01,rand(5:10),rand(5:10)])
		push!(mixands,tmp); 
	end


	return MixtureModel(mixands); 

end

function generate_o(::MAP_Push_POMDP, s::Vector{Float64}, a::Int64, sp::Vector{Float64}, rng::AbstractRNG)

	global robotViewRadius
	global objectModels

	#1: existance of human push
	#2: object reference
	#3: class reference
	#4: positive/negative
	#5: robot proximity

	#classes: 0:Near, 1:East, 2:South, 3:West, 4:North

	obs = [0,0,0,0,0]; 

	#probability of human push is around 1/10th
	pHuman = 1/10; 
	flipExist = rand(1:1);

	flipPos = rand(1:2);
	obs[4] = flipPos

	if flipExist == 1
		#then there's a human obs
		obs[1] = 1; 

		#which object was it about? 
		flipObj = rand(0:length(objectModels));

		if flipObj == 0
			#then it was about the cop
			obs[2] = 0;
			if sqrt((s[1]-s[3])*(s[1]-s[3]) + (s[2]-s[4])*(s[2]-s[4])) < robotViewRadius && flipPos == 1
				obs[3] = 0; 
			elseif sqrt((s[1]-s[3])*(s[1]-s[3]) + (s[2]-s[4])*(s[2]-s[4])) > robotViewRadius && flipPos == 0
				obs[3] = 0; 
			elseif abs(s[1]-s[3]) > abs(s[2]-s[4]) && s[1]-s[3] > 0 && flipPos == 1
				obs[3] = 1; 
			elseif !(abs(s[1]-s[3]) > abs(s[2]-s[4]) && s[1]-s[3] > 0) && flipPos == 0
				obs[3] = 1; 
			elseif abs(s[1]-s[3]) > abs(s[2]-s[4]) && s[1]-s[3] < 0 && flipPos == 1
				obs[3] = 3; 
			elseif !(abs(s[1]-s[3]) > abs(s[2]-s[4]) && s[1]-s[3] < 0) && flipPos == 0
				obs[3] = 3; 
			elseif abs(s[1]-s[3]) < abs(s[2]-s[4]) && s[2]-s[4] > 0 && flipPos == 1
				obs[3] = 4; 
			elseif !(abs(s[1]-s[3]) < abs(s[2]-s[4]) && s[2]-s[4] > 0) && flipPos == 0
				obs[3] = 4;
			elseif abs(s[1]-s[3]) < abs(s[2]-s[4]) && s[2]-s[4] < 0 && flipPos == 1
				obs[3] = 2; 
			elseif !(abs(s[1]-s[3]) < abs(s[2]-s[4]) && s[2]-s[4] < 0) && flipPos == 0
				obs[3] = 2;
			end
		else
			#it was about objectModels[flipObj]

			centX = objectModels[flipObj][1]; 
			centY = objectModels[flipObj][2]; 
			radX = objectModels[flipObj][3];
			radY = objectModels[flipObj][4];

			distX = centX - s[3]; 
			distY = centY - s[4]

			obs[2] = flipObj; 



			if abs(distX) < radX && abs(distY) < radY && flipPos == 1
				obs[3] = 0
			elseif !(abs(distX) < radX && abs(distY) < radY) && flipPos == 0
				obs[3] = 0; 
			elseif abs(distX) > abs(distY) && distX > 0 && flipPos == 1
				obs[3] = 1
			elseif !(abs(distX) > abs(distY) && distX > 0) && flipPos == 0
				obs[3] = 1;
			elseif abs(distX) > abs(distY) && distX < 0 && flipPos == 1
				obs[3] = 3
			elseif !(abs(distX) > abs(distY) && distX < 0) && flipPos == 0
				obs[3] = 3;
			elseif abs(distX) < abs(distY) && distY > 0 && flipPos == 1
				obs[3] = 4
			elseif !(abs(distX) < abs(distY) && distY > 0) && flipPos == 0
				obs[3] = 4;
			elseif abs(distX) < abs(distY) && distY < 0 && flipPos == 1
				obs[3] = 2
			elseif !(abs(distX) < abs(distY) && distY < 0) && flipPos == 0
				obs[3] = 2;
			end

		end

	end



	if sqrt((s[1]-s[3])*(s[1]-s[3]) + (s[2]-s[4])*(s[2]-s[4])) < robotViewRadius/2
		obs[5] = 2; 
	elseif sqrt((s[1]-s[3])*(s[1]-s[3]) + (s[2]-s[4])*(s[2]-s[4])) < robotViewRadius
		obs[5] = 1;  
	else
		obs[5] = 0; 
	end

	return obs; 

end



function obs_weight(::MAP_Push_POMDP, s::Vector{Float64}, a::Int64, sp::Vector{Float64}, o::Vector{Int64})

	global robotViewRadius
	global objectModels

	#1: existance of human push
	#2: object reference
	#3: class reference
	#4: positive/negative
	#5: robot proximity

	#check existance of human push
	
	prob = 1; 



	if o[1] == 1

		if o[2] == 0
			#then it was about the cop
			if sqrt((s[1]-s[3])*(s[1]-s[3]) + (s[2]-s[4])*(s[2]-s[4])) < robotViewRadius && o[4] == 1
				if o[3] == 0
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif sqrt((s[1]-s[3])*(s[1]-s[3]) + (s[2]-s[4])*(s[2]-s[4])) > robotViewRadius && o[4] == 0
				if o[3] == 0
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif abs(s[1]-s[3]) > abs(s[2]-s[4]) && s[1]-s[3] > 0 && o[4] == 1
				if o[3] == 1
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif !(abs(s[1]-s[3]) > abs(s[2]-s[4]) && s[1]-s[3] > 0) && o[4] == 0
				if o[3] == 1
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif abs(s[1]-s[3]) > abs(s[2]-s[4]) && s[1]-s[3] < 0 && o[4] == 1
				if o[3] == 3 
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif !(abs(s[1]-s[3]) > abs(s[2]-s[4]) && s[1]-s[3] < 0) && o[4] == 0
				if o[3] == 3 
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif abs(s[1]-s[3]) < abs(s[2]-s[4]) && s[2]-s[4] > 0 && o[4] == 1
				if o[3] == 4 
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif !(abs(s[1]-s[3]) < abs(s[2]-s[4]) && s[2]-s[4] > 0) && o[4] == 0
				if o[3] == 4
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif abs(s[1]-s[3]) < abs(s[2]-s[4]) && s[2]-s[4] < 0 && o[4] == 1
				if o[3] == 2
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif !(abs(s[1]-s[3]) < abs(s[2]-s[4]) && s[2]-s[4] < 0) && o[4] == 0
				if o[3] == 2
					prob = prob*.95
				else
					prob = prob*.05
				end
			end
		else


			centX = objectModels[o[2]][1]; 
			centY = objectModels[o[2]][2]; 
			radX = objectModels[o[2]][3];
			radY = objectModels[o[2]][4];

			distX = centX - s[3]; 
			distY = centY - s[4]



			if abs(distX) < radX && abs(distY) < radY && o[4] == 1
				if o[3] == 0
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif !(abs(distX) < radX && abs(distY) < radY) && o[4] == 0
				if o[3] == 0 
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif abs(distX) > abs(distY) && distX > 0 && o[4] == 1
				if o[3] == 1
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif !(abs(distX) > abs(distY) && distX > 0) && o[4] == 0
				if o[3] == 1
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif abs(distX) > abs(distY) && distX < 0 && o[4] == 1
				if o[3] == 3
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif !(abs(distX) > abs(distY) && distX < 0) && o[4] == 0
				if o[3] == 3
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif abs(distX) < abs(distY) && distY > 0 && o[4] == 1
				if o[3] == 4
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif !(abs(distX) < abs(distY) && distY > 0) && o[4] == 0
				if o[3] == 4
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif abs(distX) < abs(distY) && distY < 0 && o[4] == 1
				if o[3] == 2
					prob = prob*.95
				else
					prob = prob*.05
				end
			elseif !(abs(distX) < abs(distY) && distY < 0) && o[4] == 0
				if o[3] == 2
					prob = prob*.95
				else
					prob = prob*.05
				end
			end

		end

	end

	if o[5] == 2
		if sqrt((s[1]-s[3])*(s[1]-s[3]) + (s[2]-s[4])*(s[2]-s[4])) < robotViewRadius/2
			prob = prob*.75; 
		elseif sqrt((s[1]-s[3])*(s[1]-s[3]) + (s[2]-s[4])*(s[2]-s[4])) < robotViewRadius
			prob = prob*.2;  
		else
			prob = prob*.05; 
		end
	elseif o[5]==1
		if sqrt((s[1]-s[3])*(s[1]-s[3]) + (s[2]-s[4])*(s[2]-s[4])) < robotViewRadius/2
			prob = prob*.05; 
		elseif sqrt((s[1]-s[3])*(s[1]-s[3]) + (s[2]-s[4])*(s[2]-s[4])) < robotViewRadius
			prob = prob*.90;  
		else
			prob = prob*.05; 
		end
	else
		if sqrt((s[1]-s[3])*(s[1]-s[3]) + (s[2]-s[4])*(s[2]-s[4])) < robotViewRadius/2
			prob = prob*.01; 
		elseif sqrt((s[1]-s[3])*(s[1]-s[3]) + (s[2]-s[4])*(s[2]-s[4])) < robotViewRadius
			prob = prob*.04;  
		else
			prob = prob*.95; 
		end
	end



	return prob; 


end


function generate_s(p::MAP_Push_POMDP, s::Vector{Float64}, a::Int, rng::AbstractRNG)
	sig_0 = [1.,1.,8.,8.]

	d= MvNormal(sig_0)
    noise = rand(d::MvNormal) 

    noise[1] = 0; 
    noise[2] = 0; 

    if a == 2
        s= s + [-10.,0.,0.,0.] + noise
    elseif a == 3
        s= s + [10.,0.,0.,0.] + noise
    elseif a == 1
    	s= s + [0.,10.,0.,0.] + noise
    elseif a == 0
    	s= s + [0.,-10.,0.,0.] + noise
    else 
    	s= s + noise
    end

    #s[1] = max(0,s[1])
    #s[1] = min(437,s[1]); 
    #s[2] = max(0,s[2])
    #s[2] = min(754,s[2]);
    #s[3] = max(0,s[3])
    #s[3] = min(437,s[3]); 
    #s[4] = max(0,s[4])
    #s[4] = min(754,s[4]);

    return s   
    

end



function reward(p::MAP_Push_POMDP, s::Vector{Float64}, a::Int)
	if sqrt((s[1]-s[3])*(s[1]-s[3]) + (s[2]-s[4])*(s[2]-s[4])) < 25
		return 5; 
	else
		return 0; 
	end

end;


MAP_Push_POMDP() = MAP_Push_POMDP(0.9, 5.0, 0.0, 1.0, 0.0)

convert_s(::Type{A}, s::Vector{Float64}, p::MAP_Push_POMDP) where A<:AbstractVector = eltype(A)[s.status, s.y]
convert_s(::Type{Vector{Float64}}, s::A, p::MAP_Push_POMDP) where A<:AbstractVector = Vector{Float64}(Int64(s[1]), s[2])


global pomdp
global up
global solver
global planner
global bel
global parseBel
global action
global objectModels

objectModels = Any[]


function create(copPose::Vector{Int64})
	
	global pomdp
	global up
	global solver
	global planner
	global bel
	global robotViewRadius
	global objectModels

	robotViewRadius = 50; 

	#println("copPose"); 
	#println(copPose); 

	discount(p::MAP_Push_POMDP) = p.discount_factor
	actions(::MAP_Push_POMDP) = [0,1,2,3]
	n_actions(p::MAP_Push_POMDP) = length(actions(p))


	pomdp = MAP_Push_POMDP(); 
	b0 = initialstate_distribution(pomdp,copPose);


	N = 100000; 
	RNG = MersenneTwister(1)
	up = SIRParticleFilter(pomdp,N,RNG);
	bel = initialize_belief(up,b0); 
	#println(mode(bel))

	solver = POMCPSolver(max_time=1, c=10.0,max_depth=1000)
	planner = solve(solver,pomdp); 

end


function recreate(copPose::Vector{Int64})
	
	global pomdp
	global up
	global solver
	global planner
	global bel
	global robotViewRadius
	global objectModels


	#println("copPose"); 
	#println(copPose); 

	discount(p::MAP_Push_POMDP) = p.discount_factor
	actions(::MAP_Push_POMDP) = [0,1,2,3]


	pomdp = MAP_Push_POMDP(); 
	b0 = initialstate_distribution(pomdp,copPose);


	N = 100000; 
	RNG = MersenneTwister(1)
	up = SIRParticleFilter(pomdp,N,RNG);

	#println(mode(bel))

	solver = POMCPSolver(max_time=1, c=10.0,max_depth=1000)
	planner = solve(solver,pomdp); 

end


function getAct(o::Vector{Int64})

	global bel
	global action
	global objectModels


	println(objectModels); 
	#println(length(objectModels)); 

	MAP = mode(bel); 
	#VOI(bel); 
	#println(MAP)


	#left/right or up/down
	if abs(MAP[1]-MAP[3]) > abs(MAP[2]-MAP[4])

		#left or right
		if MAP[1] > MAP[3]
			action=2
		else
			action=3
		end

	else

		#up or down
		if MAP[2] > MAP[4]
			action=0
		else
			action=1
		end
	end

	newBel,u = update_info(up,bel,action,o)
	bel = newBel
	

	pythonifyBel(bel); 

	return action

end


function pythonifyBel(bel)
	
	global parseBel
	parseBel = []; 
	parts = particles(bel) 

	for i in 1:n_particles(bel)
		push!(parseBel,particle(bel,i)); 
	end
	
	
end


function addModel(a::Any)
	
	global objectModels

	push!(objectModels,a); 


end


function VOI(bel)

	global up
	global robotViewRadius
	
	action = 0; 


	belNo,u = update_info(up,bel,action,0)
	belYes,u = update_info(up,bel,action,1)

	VOINO = 0; 
	for i in 1:n_particles(belNo)
		s = particle(belNo,i); 
		if sqrt((s[1]-s[3])*(s[1]-s[3]) + (s[2]-s[4])*(s[2]-s[4])) < robotViewRadius
			VOINO += 5; 
		end
	end

	VOIYes = 0; 
	for i in 1:n_particles(belYes)
		s = particle(belYes,i); 
		if sqrt((s[1]-s[3])*(s[1]-s[3]) + (s[2]-s[4])*(s[2]-s[4])) < robotViewRadius
			VOIYes += 5; 
		end
	end

	println("VOI of No:")
	println(VOINO)

	println("VOI of Yes:")
	println(VOIYes)

	println("Average:")
	println((VOINO+VOIYes)/2); 

end



#create([200,200])
#addModel([180.5,382.375,100.5,118.375]); 
#getAct([1,1,2,1,0])