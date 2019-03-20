from trainers.cnn_trainer import Trainer
from models.cnn_model import CNNModel
import random
from evolve.genotype import Genome
from trainers.cnn_trainer import Trainer
import logging


class Evolution():
    def __init__(self, config, data):
        self.parents = []                                   # population of genomes (each one is a set of CNN hyperparameters)
        self.config = config
        self.data = data
        self.numGenerations = config['numGenerations']
        self.populationSize = config['populationSize']
        self.mutateProb = config['mutateProb']
        self.gene_types = list(config['hyperparams'])
        self.scored_cache = []                            # (individial, fitness_score) --> global/elitist cache of the population


    def initialise_population(self):                        # initialise population with random parameter choices
        for i in range(0, self.populationSize):

            # first do random params for convolutional layers (all possible parameters [gene types])
            conv_layers = []
            for layer_num in range(self.config['numConvLayers']):
                conv_layer = {}
                for gene_type in self.config['hyperparams']:                                    # i.e. activation is a gene type
                    gene_val = random.choice(self.config['hyperparams'][gene_type])
                    conv_layer.update({gene_type:gene_val})
                conv_layers.append(conv_layer)

            # now do random params for dense layers (only activation paramater [gene type])
            dense_layers = []
            for layer_num in range(self.config['numDenseLayers']):
                dense_layer = {}
                gene_val = random.choice(self.config['hyperparams']['activation'])
                dense_layer.update({'activation':gene_val})
                dense_layers.append(dense_layer)

            self.parents.append(Genome(conv_layers, dense_layers))


    def train_and_score(self, genome):
        """
        Train and score a single individual.
        Score (fitness) is equal to a model's accuracy on test data predictions.
        :param genome:
        :return score:
        """

        trainer = Trainer(CNNModel.buildForEvolution(genome), self.config, self.data)
        trainer.train()                                                                                 # train individual using training data
        score = trainer.model.evaluate(self.data['testX'], self.data['testY'], verbose=0)               # score individual using test data
        logging.info("Score : "+str(score[1]))                                                                 # 1=accuracy, 0=loss.
        genome.fitness = score[1]                                                                       # set the individual's fitness variable

        return score

    def evolvePopulation(self, gen):
        """
        Evolve the population of genomes (candidate parameter-sets).
        :return:
        """

        logging.info("Generation {curGen} of {totGens}".format(curGen=gen + 1, totGens=self.numGenerations))

        # Train and score population
        # ---------------------------
        logging.info("Scoring each member of the population...")
        for individual in self.parents:                                                                         # train and score population
            self.train_and_score(individual)

        #graded = [(self.train_and_score(individual), individual) for individual in self.parents]               # train and score population
        #graded = [x[1] for x in sorted(self.scored_cache, key=lambda x: x[0], reverse=True)]                   # sort on scores


        # Survival of the fittest
        # ---------------------------
        logging.info("Applying survival of the fittest...")
        self.parents = self.parents[:len(self.parents)//2]
        # bottom_half_fitnesses = self.scored_cache[:len(self.scored_cache)//2]
        # for parent in self.parents:
        #     if parent in [i[1] for i in bottom_half_fitnesses]:
        #         self.parents.remove(parent)                                                             # remove parent if it's in the bottom fitness half of the cache


        # Crossover and mutation
        # ---------------------------
        logging.info("Applying crossover and mutation...")

        num_kids_needed = self.populationSize - len(self.parents)
        print("num kids needed: "+str(num_kids_needed))

        children = []
        mating_pool = self.parents
        while(len(children) < num_kids_needed):                                                       # look at top (fittest) half of the population for breeding partners
            parent1 = random.choice(mating_pool)
            parent2 = random.choice(mating_pool)
            while(parent1 == parent2 and self.populationSize > 2):                                    # ensure that two different parents will be mating
                parent1 = random.choice(mating_pool)
            child = self.crossover(parent1, parent2)                                                  # crossover parents, produce child
            if(self.mutateProb > random.uniform(0,1)):
                self.mutate_one_gene(child)                                                           # random chance that child is mutated
            children.append(child)                                                                    # add child to list


        self.parents.extend(children)                                                                 # add children to population

        if(gen == self.numGenerations-1):
            logging.info("Evolution complete.")
            #return Trainer.compile_model(CNNModel.buildForEvolution(self.scored_cache[0][0]))


    def mutate_one_gene(self, genome):                                                  # TODO: account for random new_gene_val being the same as the old val (while loop)
        layer_to_mutate = random.choice(genome.layers)                                  # which layer to mutate?
        index_layer_to_mutate = genome.layers.index(layer_to_mutate)                    # index of chosen layer to mutate
        gene_type_to_mutate = random.choice(list(layer_to_mutate))                      # mutate which param? Activation? Dropout?
        new_gene_val = random.choice(self.config['hyperparams'][gene_type_to_mutate])   # choose a random new value for the gene
        genome.layers[index_layer_to_mutate][gene_type_to_mutate] = new_gene_val        # set new value of gene we're mutating


    def crossover(self, genomeMom, genomeDad):                                          # TODO: this crossover logic might be too splicey
        """ Create a child genome by mating two parent genomes
            - child's conv layer: split between mother and father
            - child's dense layer: activation function chosen randomly from mother or father """

        parents = [genomeMom, genomeDad]
        random.shuffle(parents)                                                         # shuffle parents so both get a fair chance to give out slightly more
                                                                                        # conv layer genes since there are an odd number of conv layers.
        child_conv_layers = []
        for cl in range(self.config['numConvLayers']):                                  # crossover conv layers
            if (cl+1)%2 == 0:
                child_conv_layers.append(parents[0].conv_layers[cl])
            else:
                child_conv_layers.append(parents[1].conv_layers[cl])

        child_dense_layers = []
        for dl in range(self.config['numDenseLayers']):                                 # crossover dense layers
            if (dl+1)%2 == 0:
                child_dense_layers.append(parents[0].dense_layers[dl])
            else:
                child_dense_layers.append(parents[1].dense_layers[dl])

        return Genome(child_conv_layers, child_dense_layers, genome_mom=genomeMom, genome_dad=genomeDad)                            # return child genome